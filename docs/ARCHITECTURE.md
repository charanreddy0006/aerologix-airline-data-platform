# AeroLogix architecture

## End-to-end architecture

```mermaid
flowchart LR
  CSV[Five synthetic CSV extracts] --> PY[Python validation and loader]
  PY --> STG[SQL Server stg schema]
  STG --> OLTP[ref and ops schemas]
  OLTP --> ETL[T-SQL warehouse procedure]
  ETL --> DW[Warehouse dimensions and facts]
  DW --> MART[Analytical mart views]
  OLTP --> DBT[dbt staging and marts]
  AIR[Separately deployed Airflow scheduler] --> PY
  AIR --> ETL
```

## Data flow

```mermaid
flowchart TD
  G[Seeded synthetic generator] --> A[airports.csv]
  G --> AC[aircraft.csv]
  G --> R[routes.csv]
  G --> F[flights.csv]
  G --> B[bookings.csv]
  A --> L[Header and row validation]
  AC --> L
  R --> L
  F --> L
  B --> L
  L --> S[Transactional staging load]
  S --> P[etl.usp_ApplyOperationalLoad]
  P --> O[Normalized OLTP]
  O --> W[etl.usp_LoadWarehouse]
  W --> D[Dimensions, facts and service-date snapshot]
```

## OLTP physical ERD

Airport and aircraft are reference data; routes are directed. Airline and crew are not modeled because extracts contain no ownership or crew assignments. Maintenance is modeled but has no generated feed.

```mermaid
erDiagram
  AIRPORT ||--o{ ROUTE : origin
  AIRPORT ||--o{ ROUTE : destination
  ROUTE ||--o{ FLIGHT : serves
  AIRCRAFT ||--o{ FLIGHT : assigned
  FLIGHT ||--o{ BOOKING : carries
  PASSENGER ||--o{ BOOKING : makes
  AIRCRAFT ||--o{ MAINTENANCE_EVENT : receives
```

## Warehouse star schema

```mermaid
erDiagram
  DIM_DATE ||--o{ FACT_FLIGHT : service_date
  DIM_AIRPORT ||--o{ FACT_FLIGHT : origin_or_destination
  DIM_AIRCRAFT ||--o{ FACT_FLIGHT : aircraft
  DIM_DATE ||--o{ FACT_BOOKING : service_date
  DIM_AIRPORT ||--o{ FACT_BOOKING : origin_or_destination
  DIM_PASSENGER ||--o{ FACT_BOOKING : passenger
  DIM_DATE ||--o{ FACT_DAILY_FLIGHT_SNAPSHOT : service_date
```

FactFlight is one row per FlightId; FactBooking is one row per BookingId; FactDailyFlightSnapshot is one current aggregate per service date and flight. Reruns refresh that service-date aggregate; it is not a load-date history. Airport is SCD2, aircraft is SCD1 with previous type SCD3, and passenger loyalty is SCD1. Airport effective dates are processing-time UTC because extracts contain no effective timestamp, so historical as-of airport attribution is limited.

## Airflow workflow

```mermaid
flowchart LR
  A[Load and validate all source CSVs] --> B[Apply OLTP upserts]
  B --> C[Load dimensional warehouse]
```

Compose starts SQL Server only. Airflow needs a separate scheduler, metadata database, matching constraints, and an `aerologix_sqlserver` connection. See [setup](SETUP_GUIDE.md) and [pipeline](PIPELINE_GUIDE.md).
