# Data dictionary

| Relation | Grain / key | Purpose |
|---|---|---|
| `ref.Airport` | Airport / AirportCode | Name, city, country and timezone |
| `ref.Aircraft` | Aircraft / AircraftId | Type, capacity, manufacture year and status |
| `ref.Route` | Directed route / RouteId | Airport endpoints and positive distance |
| `ops.Passenger` | Synthetic passenger / PassengerId | Loyalty tier and creation timestamp |
| `ops.Flight` | Flight / FlightId | Service date, schedule, route, aircraft and state |
| `ops.Booking` | Booking / BookingId | Passenger, seat, cabin, fare and lifecycle |
| `ops.MaintenanceEvent` | Maintenance event / MaintenanceId | Aircraft service interval and cost |
| `dw.DimDate` | Calendar day / DateKey (YYYYMMDD) | Calendar attributes |
| `dw.DimAirport` | Airport version / AirportKey | SCD Type 2 airport attributes |
| `dw.DimAircraft` | Aircraft / AircraftKey | Type 1 attributes and previous type (Type 3) |
| `dw.DimPassenger` | Passenger / PassengerKey | Loyalty tier and first/last seen dates |
| `dw.DimRoute` | Route / RouteKey | Airport role keys and distance |
| `dw.FactFlight` | One row per flight | Status, delay, miles and count flags |
| `dw.FactBooking` | One row per booking | Booking state, fare and cabin |
| `dw.FactDailyFlightSnapshot` | One flight per service date | Current service-date status, booking count and fare aggregate |

Fares and maintenance costs are USD; distances are statute miles. Cancelled booking fare is excluded from snapshot and revenue aggregates; the booking fact retains the source fare and latest status. Delay is non-additive. The warehouse has no operational crew bridge because no crew assignment source is provided.
