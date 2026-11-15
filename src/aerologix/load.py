"""Validated, transactional CSV ingestion into AeroLogix SQL Server staging."""
from __future__ import annotations

import argparse
import csv
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

try:
    import pyodbc
except ImportError:  # permits offline validation tests; live loading still requires the driver
    pyodbc = None
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> None:
        """No-op fallback when tests run without python-dotenv installed."""

LOGGER = logging.getLogger(__name__)
NULL_VALUES = {"", "NULL", r"\N"}


@dataclass(frozen=True)
class Feed:
    filename: str
    table: str
    columns: tuple[tuple[str, str, bool], ...]  # CSV header, SQL identifier, nullable
    keys: tuple[str, ...]

    @property
    def headers(self) -> tuple[str, ...]:
        return tuple(item[0] for item in self.columns)


FEEDS = (
    Feed("airports.csv", "stg.AirportLoad", (("airport_code", "AirportCode", False), ("airport_name", "AirportName", False), ("city", "City", False), ("country_code", "CountryCode", False), ("timezone", "TimeZoneName", False)), ("airport_code",)),
    Feed("aircraft.csv", "stg.AircraftLoad", (("aircraft_id", "AircraftId", False), ("aircraft_type", "AircraftType", False), ("seat_capacity", "SeatCapacity", False), ("manufacture_year", "ManufactureYear", False), ("status", "AircraftStatus", False)), ("aircraft_id",)),
    Feed("routes.csv", "stg.RouteLoad", (("origin_airport_code", "OriginAirportCode", False), ("destination_airport_code", "DestinationAirportCode", False), ("distance_miles", "DistanceMiles", False)), ("origin_airport_code", "destination_airport_code")),
    Feed("flights.csv", "stg.FlightLoad", (("flight_id", "FlightId", False), ("flight_number", "FlightNumber", False), ("flight_date", "FlightDate", False), ("origin_airport_code", "OriginAirportCode", False), ("destination_airport_code", "DestinationAirportCode", False), ("aircraft_id", "AircraftId", False), ("scheduled_departure", "ScheduledDeparture", False), ("actual_departure", "ActualDeparture", True), ("flight_status", "FlightStatus", False), ("distance_miles", "DistanceMiles", False), ("departure_delay_minutes", "DepartureDelayMinutes", False)), ("flight_id",)),
    Feed("bookings.csv", "stg.BookingLoad", (("booking_id", "BookingId", False), ("flight_id", "FlightId", False), ("passenger_id", "PassengerId", False), ("booking_reference", "BookingReference", False), ("seat_number", "SeatNumber", False), ("base_fare_usd", "BaseFare", False), ("cabin_class", "CabinClass", False), ("booking_status", "BookingStatus", False)), ("booking_id",)),
)


class FeedValidationError(ValueError):
    """Raised when an input CSV cannot safely be loaded."""


def _normalize(value: str | None, *, nullable: bool, filename: str, column: str, row: int) -> Any:
    if value is None:
        raise FeedValidationError(f"{filename}:{row}: missing column {column!r}")
    value = value.strip()
    if value.upper() in NULL_VALUES:
        if nullable:
            return None
        raise FeedValidationError(f"{filename}:{row}: required value {column!r} is empty")
    try:
        if column in {"aircraft_id", "seat_capacity", "manufacture_year", "distance_miles", "flight_id", "aircraft_id", "departure_delay_minutes", "booking_id"}:
            return int(value)
        if column == "flight_date":
            return date.fromisoformat(value)
        if column in {"scheduled_departure", "actual_departure"}:
            return datetime.fromisoformat(value)
        if column == "base_fare_usd":
            amount = Decimal(value)
            if not amount.is_finite():
                raise InvalidOperation
            return amount
    except (ValueError, InvalidOperation) as exc:
        raise FeedValidationError(f"{filename}:{row}: invalid value {value!r} for {column!r}") from exc
    return value


def read_feed(folder: Path, feed: Feed) -> list[tuple[Any, ...]]:
    """Read and validate a feed, rejecting schema drift and duplicate source keys."""
    path = folder / feed.filename
    if not path.is_file():
        raise FeedValidationError(f"Required input file not found: {path}")
    rows: list[tuple[Any, ...]] = []
    seen: set[tuple[str, ...]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        if len(actual) != len(set(actual)):
            raise FeedValidationError(f"{feed.filename}: duplicate header names are not allowed")
        missing = sorted(set(feed.headers) - set(actual))
        extra = sorted(set(actual) - set(feed.headers))
        if missing or extra:
            raise FeedValidationError(f"{feed.filename}: header mismatch; missing={missing}, unexpected={extra}")
        for row_num, raw in enumerate(reader, start=2):
            if None in raw:
                raise FeedValidationError(f"{feed.filename}:{row_num}: row has more values than the header")
            values = tuple(_normalize(raw.get(csv_name), nullable=nullable, filename=feed.filename, column=csv_name, row=row_num) for csv_name, _, nullable in feed.columns)
            key = tuple(str(values[feed.headers.index(k)]) for k in feed.keys)
            if key in seen:
                raise FeedValidationError(f"{feed.filename}:{row_num}: duplicate business key {key}")
            seen.add(key)
            rows.append(values)
    return rows


def connection_string() -> str:
    """Build a SQL Server connection string from environment configuration."""
    password = os.getenv("SQLSERVER_PASSWORD")
    if not password:
        raise RuntimeError("SQLSERVER_PASSWORD is required; configure it in the environment or .env")
    def quote(value: str) -> str:
        return "{" + value.replace("}", "}}") + "}"

    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    server = f"{os.getenv('SQLSERVER_HOST', 'localhost')},{os.getenv('SQLSERVER_PORT', '1433')}"
    return f"DRIVER={quote(driver)};SERVER={quote(server)};DATABASE={quote(os.getenv('SQLSERVER_DATABASE', 'AeroLogix'))};UID={quote(os.getenv('SQLSERVER_USER', 'sa'))};PWD={quote(password)};TrustServerCertificate=yes"


def load(folder: str | Path, *, batch_size: int = 1000, connection_factory=None) -> dict[str, int]:
    """Validate all feeds, stage them in one transaction, and apply idempotent OLTP upserts."""
    if batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    load_dotenv()
    root = Path(folder)
    staged = [(feed, read_feed(root, feed)) for feed in FEEDS]
    LOGGER.info("Validated %s input feeds", len(staged))
    if connection_factory is None:
        if pyodbc is None:
            raise RuntimeError("pyodbc is required for SQL Server loading; install project dependencies")
        connection_factory = pyodbc.connect
    conn = connection_factory(connection_string())
    try:
        cursor = conn.cursor()
        cursor.fast_executemany = True
        counts: dict[str, int] = {}
        for feed, rows in staged:
            cursor.execute(f"DELETE FROM {feed.table}")
            sql_columns = ",".join(f"[{sql_name}]" for _, sql_name, _ in feed.columns)
            markers = ",".join("?" for _ in feed.columns)
            sql = f"INSERT INTO {feed.table} ({sql_columns}) VALUES ({markers})"
            for batch in _batches(rows, batch_size):
                cursor.executemany(sql, batch)
            counts[feed.filename] = len(rows)
            LOGGER.info("Staged %d rows from %s", len(rows), feed.filename)
        cursor.execute("EXEC etl.usp_ApplyOperationalLoad")
        conn.commit()
        LOGGER.info("Operational load committed: %s", counts)
        return counts
    except Exception:
        conn.rollback()
        LOGGER.exception("CSV load failed; transaction rolled back")
        raise
    finally:
        conn.close()


def _batches(rows: list[tuple[Any, ...]], size: int) -> Iterable[list[tuple[Any, ...]]]:
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/raw", help="folder containing the five source CSV files")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    load(args.data, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
