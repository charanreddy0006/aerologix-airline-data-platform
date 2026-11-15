"""Generate deterministic, internally consistent fictional AeroLogix CSV extracts."""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_SEED = 8212026
ROUTES = [('JFK', 'LAX', 2475), ('LAX', 'JFK', 2475), ('JFK', 'ORD', 740), ('ORD', 'DFW', 802), ('SEA', 'SFO', 679), ('ATL', 'BOS', 946), ('SFO', 'LAX', 337), ('DFW', 'JFK', 1391), ('BOS', 'ORD', 867), ('LAX', 'SEA', 954)]
AIRPORTS = [('JFK', 'John F Kennedy International', 'New York', 'US', 'America/New_York'), ('LAX', 'Los Angeles International', 'Los Angeles', 'US', 'America/Los_Angeles'), ('ORD', 'O Hare International', 'Chicago', 'US', 'America/Chicago'), ('DFW', 'Dallas Fort Worth International', 'Dallas', 'US', 'America/Chicago'), ('SEA', 'Seattle Tacoma International', 'Seattle', 'US', 'America/Los_Angeles'), ('ATL', 'Hartsfield Jackson Atlanta', 'Atlanta', 'US', 'America/New_York'), ('SFO', 'San Francisco International', 'San Francisco', 'US', 'America/Los_Angeles'), ('BOS', 'Logan International', 'Boston', 'US', 'America/New_York')]
AIRCRAFT = [('A320', 180), ('A321', 220), ('B737-800', 189), ('B787-9', 290), ('A320', 180), ('B737-800', 189)]


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    """Write UTF-8 CSV with stable newline behavior."""
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def generate(out: str | Path, flight_count: int = 120, bookings_per_flight: int = 10,
             seed: int = DEFAULT_SEED, start_date: date | str = date(2025, 1, 1),
             days: int = 84) -> None:
    """Generate five related feeds with a configurable seed, date span and volume."""
    if flight_count < 0 or bookings_per_flight < 0:
        raise ValueError('record counts cannot be negative')
    if days < 1:
        raise ValueError('days must be positive')
    if bookings_per_flight > min(capacity for _, capacity in AIRCRAFT):
        raise ValueError('bookings per flight exceeds an assigned aircraft capacity')
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
    rng = random.Random(seed)
    folder = Path(out)
    folder.mkdir(parents=True, exist_ok=True)
    write_csv(folder / 'airports.csv', ['airport_code', 'airport_name', 'city', 'country_code', 'timezone'], AIRPORTS)
    write_csv(folder / 'aircraft.csv', ['aircraft_id', 'aircraft_type', 'seat_capacity', 'manufacture_year', 'status'],
              [(1001 + i, model, capacity, 2020 + i % 5, 'ACTIVE') for i, (model, capacity) in enumerate(AIRCRAFT)])
    write_csv(folder / 'routes.csv', ['origin_airport_code', 'destination_airport_code', 'distance_miles'], ROUTES)
    flights: list[tuple[object, ...]] = []
    bookings: list[tuple[object, ...]] = []
    booking_id = 1
    for flight_id in range(1, flight_count + 1):
        origin, destination, miles = ROUTES[(flight_id - 1) % len(ROUTES)]
        service_date = start_date + timedelta(days=(flight_id - 1) % days)
        hour, minute = 6 + flight_id * 3 % 14, flight_id * 17 % 60
        delay = [0, 0, 5, 12, 24, 38, 65, -8][flight_id % 8]
        status = 'CANCELLED' if flight_id % 37 == 0 else ('DIVERTED' if flight_id % 41 == 0 else 'COMPLETED')
        scheduled = datetime.combine(service_date, datetime.min.time()).replace(hour=hour, minute=minute)
        actual = '' if status == 'CANCELLED' else (scheduled + timedelta(minutes=delay)).isoformat(timespec='seconds')
        aircraft_id = 1001 + flight_id % len(AIRCRAFT)
        flights.append((flight_id, f'AX{flight_id:04d}', service_date.isoformat(), origin, destination, aircraft_id,
                        scheduled.isoformat(timespec='seconds'), actual, status, miles, delay if actual else 0))
        for seat_index in range(1, bookings_per_flight + 1):
            booking_status = 'CANCELLED' if status == 'CANCELLED' else ['BOOKED', 'TICKETED', 'FLOWN', 'CANCELLED'][(seat_index + flight_id) % 4]
            fare = round(89 + (flight_id * 13 + seat_index * 19) % 640 + rng.randrange(4) * 0.5, 2)
            bookings.append((booking_id, flight_id, f'P{booking_id * 7919 % 9000 + 1000}', f'BK{booking_id:06d}',
                             f'{chr(65 + (seat_index - 1) // 30)}{(seat_index - 1) % 30 + 1:02d}', fare,
                             ['ECONOMY', 'ECONOMY', 'ECONOMY', 'BUSINESS'][seat_index % 4], booking_status))
            booking_id += 1
    write_csv(folder / 'flights.csv', ['flight_id', 'flight_number', 'flight_date', 'origin_airport_code', 'destination_airport_code', 'aircraft_id', 'scheduled_departure', 'actual_departure', 'flight_status', 'distance_miles', 'departure_delay_minutes'], flights)
    write_csv(folder / 'bookings.csv', ['booking_id', 'flight_id', 'passenger_id', 'booking_reference', 'seat_number', 'base_fare_usd', 'cabin_class', 'booking_status'], bookings)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/raw')
    parser.add_argument('--flights', type=int, default=120)
    parser.add_argument('--bookings-per-flight', type=int, default=10)
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--start-date', default='2025-01-01', help='ISO date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=84, help='number of service days in the generated period')
    args = parser.parse_args()
    generate(args.output, args.flights, args.bookings_per_flight, args.seed, args.start_date, args.days)


if __name__ == '__main__':
    main()
