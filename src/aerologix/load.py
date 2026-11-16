"""Validated, transactional CSV ingestion into AeroLogix SQL Server staging."""
from __future__ import annotations

import argparse
import csv
import logging
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
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


def read_feed_resilient(folder: Path, feed: Feed) -> tuple[list[tuple[Any, ...]], list[dict[str, Any]]]:
    """Validate a feed while retaining each rejected source row and its reason."""
    path = folder / feed.filename
    if not path.is_file():
        raise FeedValidationError(f"Required input file not found: {path}")
    accepted: list[tuple[Any, ...]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = tuple(reader.fieldnames or ())
        if len(actual) != len(set(actual)) or set(actual) != set(feed.headers):
            raise FeedValidationError(f"{feed.filename}: header mismatch; expected={feed.headers}, actual={actual}")
        for row_num, raw in enumerate(reader, start=2):
            try:
                if None in raw:
                    raise FeedValidationError("row has more values than the header")
                values = tuple(_normalize(raw.get(csv_name), nullable=nullable, filename=feed.filename,
                                           column=csv_name, row=row_num)
                               for csv_name, _, nullable in feed.columns)
                key = tuple(str(values[feed.headers.index(k)]) for k in feed.keys)
                if key in seen:
                    raise FeedValidationError(f"duplicate business key {key}")
                seen.add(key)
                accepted.append(values)
            except FeedValidationError as exc:
                rejected.append({"row_number": row_num, "record": raw, "reason": str(exc)})
    return accepted, rejected


class JsonLogFormatter(logging.Formatter):
    """Emit one structured JSON object per log event without serializing secrets."""
    def format(self, record: logging.LogRecord) -> str:
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                   "level": record.levelname, "logger": record.name, "message": record.getMessage()}
        for key in ("execution_id", "feed", "source_records", "rejected_records", "inserted_records",
                    "updated_records", "duration_seconds", "status"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            error = record.exc_info[1]
            payload["exception_type"] = type(error).__name__
            payload["failure_details"] = str(error)[:2000]
        return json.dumps(payload, default=str)


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


def connection_string(database: str | None = None) -> str:
    """Build a SQL Server connection string from environment configuration."""
    password = os.getenv("SQLSERVER_PASSWORD")
    if not password:
        raise RuntimeError("SQLSERVER_PASSWORD is required; configure it in the environment or .env")
    def quote(value: str) -> str:
        return "{" + value.replace("}", "}}") + "}"

    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    server = f"{os.getenv('SQLSERVER_HOST', 'localhost')},{os.getenv('SQLSERVER_PORT', '1433')}"
    target_database = database or os.getenv('SQLSERVER_DATABASE', 'AeroLogix')
    return f"DRIVER={quote(driver)};SERVER={quote(server)};DATABASE={quote(target_database)};UID={quote(os.getenv('SQLSERVER_USER', 'sa'))};PWD={quote(password)};TrustServerCertificate=yes"


def load(folder: str | Path, *, batch_size: int = 1000, connection_factory=None,
         quarantine_dir: str | Path = "data/quarantine") -> dict[str, int]:
    """Load valid rows transactionally and preserve invalid rows in JSONL quarantine."""
    if batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    load_dotenv()
    root = Path(folder)
    execution_id = str(uuid.uuid4())
    started = time.monotonic()
    quarantine_root = Path(quarantine_dir)
    staged = []
    total_rejected = 0
    counts: dict[str, int] = {}
    for feed in FEEDS:
        try:
            rows, rejected = read_feed_resilient(root, feed)
        except Exception:
            LOGGER.exception("Source feed could not be validated", extra={"execution_id": execution_id,
                           "feed": feed.filename, "duration_seconds": round(time.monotonic() - started, 3),
                           "status": "FAILED"})
            raise
        counts[feed.filename] = len(rows)
        total_rejected += len(rejected)
        if rejected:
            quarantine_root.mkdir(parents=True, exist_ok=True)
            path = quarantine_root / f"{execution_id}-{feed.filename}.jsonl"
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                for item in rejected:
                    handle.write(json.dumps({"execution_id": execution_id, "feed": feed.filename, **item}, ensure_ascii=False) + "\n")
            LOGGER.warning("Quarantined rejected source rows", extra={"execution_id": execution_id,
                           "feed": feed.filename, "source_records": len(rows) + len(rejected),
                           "rejected_records": len(rejected)})
        staged.append((feed, rows))
    source_total = sum(counts.values()) + total_rejected
    LOGGER.info("Validated source feeds", extra={"execution_id": execution_id, "source_records": source_total,
                "rejected_records": total_rejected})
    if connection_factory is None:
        if pyodbc is None:
            LOGGER.error("pyodbc is required for SQL Server loading", extra={"execution_id": execution_id,
                         "source_records": source_total, "rejected_records": total_rejected,
                         "duration_seconds": round(time.monotonic() - started, 3), "status": "FAILED"})
            raise RuntimeError("pyodbc is required for SQL Server loading; install project dependencies")
        connection_factory = pyodbc.connect
    try:
        conn = connection_factory(connection_string())
    except Exception:
        LOGGER.exception("Could not connect to SQL Server", extra={"execution_id": execution_id,
                       "source_records": source_total, "rejected_records": total_rejected,
                       "duration_seconds": round(time.monotonic() - started, 3), "status": "FAILED"})
        raise
    data_committed = False
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT etl.PipelineRun(ExecutionId,StartedAt,Status,SourceRecordCount,RejectedRecordCount) VALUES(?,SYSUTCDATETIME(),'RUNNING',?,?)",
                       execution_id, source_total, total_rejected)
        conn.commit()
        cursor.fast_executemany = True
        for feed, rows in staged:
            cursor.execute(f"DELETE FROM {feed.table}")
            sql_columns = ",".join(f"[{sql_name}]" for _, sql_name, _ in feed.columns)
            markers = ",".join("?" for _ in feed.columns)
            sql = f"INSERT INTO {feed.table} ({sql_columns}) VALUES ({markers})"
            for batch in _batches(rows, batch_size):
                cursor.executemany(sql, batch)
            LOGGER.info("Staged %d valid rows from %s", len(rows), feed.filename,
                        extra={"execution_id": execution_id, "feed": feed.filename,
                               "source_records": len(rows)})
        match_queries = {
            "airports.csv": "SELECT COUNT(*) FROM stg.AirportLoad s JOIN ref.Airport t ON t.AirportCode=s.AirportCode",
            "aircraft.csv": "SELECT COUNT(*) FROM stg.AircraftLoad s JOIN ref.Aircraft t ON t.AircraftId=s.AircraftId",
            "routes.csv": "SELECT COUNT(*) FROM stg.RouteLoad s JOIN ref.Route t ON t.OriginAirportCode=s.OriginAirportCode AND t.DestinationAirportCode=s.DestinationAirportCode",
            "flights.csv": "SELECT COUNT(*) FROM stg.FlightLoad s JOIN ops.Flight t ON t.FlightId=s.FlightId",
            "bookings.csv": "SELECT COUNT(*) FROM stg.BookingLoad s JOIN ops.Booking t ON t.BookingId=s.BookingId",
        }
        updated_count = sum(int(cursor.execute(match_queries[name]).fetchone()[0]) for name in counts)
        inserted_count = sum(counts.values()) - updated_count
        cursor.execute("EXEC etl.usp_ApplyOperationalLoad")
        conn.commit()
        data_committed = True
        elapsed = round(time.monotonic() - started, 3)
        cursor.execute("UPDATE etl.PipelineRun SET FinishedAt=SYSUTCDATETIME(),Status='SUCCEEDED',FeedCountsJson=?,InsertedRecordCount=?,UpdatedRecordCount=?,DurationSeconds=? WHERE ExecutionId=?",
                       json.dumps(counts, sort_keys=True), inserted_count, updated_count, elapsed, execution_id)
        conn.commit()
        LOGGER.info("Operational load committed", extra={"execution_id": execution_id, "source_records": source_total,
                    "rejected_records": total_rejected, "inserted_records": inserted_count,
                    "updated_records": updated_count, "duration_seconds": elapsed, "status": "SUCCEEDED"})
        return counts
    except Exception as exc:
        conn.rollback()
        elapsed = round(time.monotonic() - started, 3)
        try:
            audit_status = "AUDIT_FAILED" if data_committed else "FAILED"
            detail = ("Data transaction committed, but audit finalization failed: " if data_committed else "") + str(exc)
            cursor.execute("UPDATE etl.PipelineRun SET FinishedAt=SYSUTCDATETIME(),Status=?,FailureDetails=?,FeedCountsJson=?,DurationSeconds=? WHERE ExecutionId=?",
                           audit_status, detail[:2000], json.dumps(counts, sort_keys=True), elapsed, execution_id)
            conn.commit()
        except Exception:
            conn.rollback()
            LOGGER.exception("Could not persist pipeline failure audit", extra={"execution_id": execution_id})
        LOGGER.exception("CSV load or audit finalization failed", extra={"execution_id": execution_id,
                       "source_records": source_total, "rejected_records": total_rejected,
                       "duration_seconds": elapsed, "status": "AUDIT_FAILED" if data_committed else "FAILED"})
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
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), handlers=[handler], force=True)
    load(args.data, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
