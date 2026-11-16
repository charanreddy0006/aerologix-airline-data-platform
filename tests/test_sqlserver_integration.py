"""Optional SQL Server tests. Write scenarios require an explicitly disposable instance."""
import os
import unittest

try:
    import pyodbc
except ImportError:
    pyodbc = None

HAS_DSN = bool(os.getenv("AEROLOGIX_TEST_DSN") and pyodbc)
ALLOW_WRITES = os.getenv("AEROLOGIX_TEST_WRITES") == "1"


@unittest.skipUnless(HAS_DSN, "requires AEROLOGIX_TEST_DSN and pyodbc")
class SqlServerIntegration(unittest.TestCase):
    def connect(self):
        return pyodbc.connect(os.environ["AEROLOGIX_TEST_DSN"])

    def test_load_warehouse_migration_and_snapshot_grains(self):
        with self.connect() as connection:
            cursor = connection.cursor()
            self.assertEqual(cursor.execute("SELECT COUNT(*) FROM ops.Flight").fetchone()[0], 120)
            self.assertEqual(cursor.execute("SELECT COUNT(*) FROM ops.Booking").fetchone()[0], 1200)
            self.assertEqual(cursor.execute("SELECT COUNT(*) FROM dw.FactFlight").fetchone()[0], 120)
            self.assertEqual(cursor.execute("SELECT COUNT(*) FROM dw.FactBooking").fetchone()[0], 1200)
            self.assertEqual(cursor.execute("SELECT COUNT(*) FROM dw.DimAirport WHERE IsCurrent=1").fetchone()[0], 8)
            self.assertEqual(cursor.execute("SELECT COUNT(*) FROM etl.SchemaMigration").fetchone()[0], 2)
            mismatch = cursor.execute("""
                SELECT COUNT(*) FROM ops.Flight f
                LEFT JOIN dw.FactDailyFlightSnapshot s
                  ON s.FlightId=f.FlightId AND s.SnapshotDateKey=CONVERT(int,CONVERT(char(8),f.FlightDate,112))
                OUTER APPLY (SELECT COUNT(*) BookingCount,
                    COALESCE(SUM(CASE WHEN b.BookingStatus<>'CANCELLED' THEN b.BaseFare ELSE 0 END),0) Revenue
                    FROM ops.Booking b WHERE b.FlightId=f.FlightId) x
                WHERE s.FlightId IS NULL OR s.BookingCount<>x.BookingCount OR s.Revenue<>x.Revenue
            """).fetchone()[0]
            self.assertEqual(mismatch, 0)

    @unittest.skipUnless(ALLOW_WRITES, "write checks require AEROLOGIX_TEST_WRITES=1 on a disposable SQL Server")
    def test_check_unique_and_foreign_key_constraints(self):
        # Each expected constraint failure rolls back its transaction. This suite must
        # run only on the dedicated ephemeral SQL Server in CI or a disposable instance.
        cases = (
            ("INSERT ref.Aircraft(AircraftId,AircraftType,SeatCapacity,ManufactureYear,AircraftStatus) VALUES(-990001,'TEST',0,2024,'ACTIVE')", "check"),
            ("INSERT ops.Flight(FlightId,FlightNumber,FlightDate,RouteId,AircraftId,ScheduledDeparture,FlightStatus,DepartureDelayMinutes) VALUES(-990001,'ZX990001','2040-01-01',-990001,-990001,'2040-01-01','SCHEDULED',0)", "foreign key"),
            ("INSERT ops.Flight(FlightId,FlightNumber,FlightDate,RouteId,AircraftId,ScheduledDeparture,FlightStatus,DepartureDelayMinutes) SELECT FlightId,'ZXPKTEST',FlightDate,RouteId,AircraftId,ScheduledDeparture,FlightStatus,DepartureDelayMinutes FROM ops.Flight WHERE FlightId=1", "primary key"),
            ("INSERT ops.Flight(FlightId,FlightNumber,FlightDate,RouteId,AircraftId,ScheduledDeparture,FlightStatus,DepartureDelayMinutes) SELECT -990002,FlightNumber,FlightDate,RouteId,AircraftId,ScheduledDeparture,FlightStatus,DepartureDelayMinutes FROM ops.Flight WHERE FlightId=1", "unique flight number/date"),
        )
        for statement, name in cases:
            with self.subTest(constraint=name), self.connect() as connection:
                with self.assertRaises(pyodbc.Error):
                    connection.cursor().execute(statement)
                connection.rollback()

    @unittest.skipUnless(ALLOW_WRITES, "SCD scenario requires AEROLOGIX_TEST_WRITES=1 on a disposable SQL Server")
    def test_airport_scd2_and_transaction_rollback(self):
        with self.connect() as connection:
            cursor = connection.cursor()
            original = cursor.execute("SELECT AirportName FROM ref.Airport WHERE AirportCode='JFK'").fetchone()[0]
            cursor.execute("UPDATE ref.Airport SET AirportName=? WHERE AirportCode='JFK'", original + " Rollback")
            connection.rollback()
            self.assertEqual(cursor.execute("SELECT AirportName FROM ref.Airport WHERE AirportCode='JFK'").fetchone()[0], original)
            changed = original + " Phase3"
            cursor.execute("UPDATE ref.Airport SET AirportName=? WHERE AirportCode='JFK'", changed)
            connection.commit()
            try:
                cursor.execute("EXEC etl.usp_LoadWarehouse")
                connection.commit()
                versions = cursor.execute("SELECT COUNT(*) FROM dw.DimAirport WHERE AirportCode='JFK'").fetchone()[0]
                current = cursor.execute("SELECT COUNT(*) FROM dw.DimAirport WHERE AirportCode='JFK' AND IsCurrent=1 AND AirportName=?", changed).fetchone()[0]
                self.assertGreaterEqual(versions, 2)
                self.assertEqual(current, 1)
                cursor.execute("UPDATE ref.Airport SET AirportName=? WHERE AirportCode='JFK'", original)
                connection.commit()
                cursor.execute("EXEC etl.usp_LoadWarehouse")
                connection.commit()
            finally:
                # Restore source and warehouse state even if an assertion fails.
                cursor.execute("UPDATE ref.Airport SET AirportName=? WHERE AirportCode='JFK'", original)
                connection.commit()
                cursor.execute("EXEC etl.usp_LoadWarehouse")
                connection.commit()
