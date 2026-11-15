# Data model

See [architecture diagrams](ARCHITECTURE.md) and [data dictionary](DATA_DICTIONARY.md).

## OLTP

`ref.Airport` is keyed by three-character airport code; `ref.Aircraft` by source aircraft ID; `ref.Route` by identity RouteId and unique directed airport pair. `ops.Flight` has a source FlightId primary key and unique flight number/date, and references one route and aircraft. `ops.Passenger` is keyed by synthetic PassengerId. `ops.Booking` is keyed by BookingId, has a unique booking reference and unique seat per flight, and references a flight and passenger. `ops.MaintenanceEvent` records maintenance intervals and costs.

Airline and crew members are not represented because the supplied feed has no airline ownership or crew assignment attributes. The starter warehouse's incomplete `dw.BridgeFlightCrew` table was removed from new initializations: it had no crew entity or referential integrity and could not support a valid relationship. Add a crew bridge only with a sourced crew-member entity and assignment feed.

## Warehouse grains

| Table | Grain | Measures / behavior |
|---|---|---|
| `dw.FactFlight` | One row per source FlightId | Flight count flags, distance, delay and status |
| `dw.FactBooking` | One row per source BookingId | Fare, booking count, cabin and current lifecycle status |
| `dw.FactDailyFlightSnapshot` | One row per service-date key and FlightId | Current corrected booking count, status and non-cancelled fare total for the service date |

`DimDate` uses integer YYYYMMDD. Airport uses SCD Type 2 with a current-row flag and validity interval. Aircraft updates in place (Type 1) and keeps `PreviousAircraftType` (Type 3). Passenger loyalty tier updates in place (Type 1). Airport source rows lack effective dates, so recorded SCD dates are processing times, not authoritative event effective dates. New facts use the current airport version; reruns preserve an existing airport surrogate key while its airport natural key is unchanged. Historical as-of attribution cannot be proven from the supplied source extracts.

