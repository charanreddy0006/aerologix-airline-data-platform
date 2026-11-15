"""Offline integration checks for checked-in synthetic project assets."""
import csv
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from aerologix.generate import generate


def read_csv(name: str) -> list[dict[str, str]]:
    """Read a checked-in raw CSV file."""
    with (ROOT / 'data' / 'raw' / f'{name}.csv').open(
        newline='', encoding='utf-8'
    ) as handle:
        return list(csv.DictReader(handle))


class ProjectTests(unittest.TestCase):
    """Check source relationships and project deliverables without SQL Server."""

    def test_checked_in_relations(self) -> None:
        """Verify the five extracts have consistent route, fleet and booking keys."""
        aircraft_ids = {int(row['aircraft_id']) for row in read_csv('aircraft')}
        routes = {
            (row['origin_airport_code'], row['destination_airport_code'])
            for row in read_csv('routes')
        }
        flights = read_csv('flights')
        bookings = read_csv('bookings')
        flight_ids = {int(row['flight_id']) for row in flights}

        self.assertEqual(len(flights), 120)
        self.assertEqual(len(bookings), 1200)
        for flight in flights:
            route = (flight['origin_airport_code'], flight['destination_airport_code'])
            self.assertIn(route, routes)
            self.assertIn(int(flight['aircraft_id']), aircraft_ids)
            if flight['actual_departure']:
                actual = datetime.fromisoformat(flight['actual_departure'])
                scheduled = datetime.fromisoformat(flight['scheduled_departure'])
                delay = (actual - scheduled).total_seconds() / 60
                self.assertEqual(delay, int(flight['departure_delay_minutes']))
        for booking in bookings:
            self.assertIn(int(booking['flight_id']), flight_ids)

    def test_generator_is_repeatable(self) -> None:
        """Repeated generation with the same seed emits byte-identical CSVs."""
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            generate(first, 12, 3)
            generate(second, 12, 3)
            for name in ('flights.csv', 'bookings.csv'):
                self.assertEqual(
                    (Path(first) / name).read_bytes(),
                    (Path(second) / name).read_bytes(),
                )

    def test_sql_and_model_assets_present(self) -> None:
        """Ensure core SQL, dbt and Airflow deliverables remain in the project."""
        assets = (
            'sql/oltp/01_database.sql',
            'sql/warehouse/01_warehouse.sql',
            'sql/warehouse/02_load.sql',
            'dbt/dbt_project.yml',
            'airflow/dags/aerologix_daily.py',
        )
        for asset in assets:
            with self.subTest(asset=asset):
                self.assertTrue((ROOT / asset).is_file())


if __name__ == '__main__':
    unittest.main()
