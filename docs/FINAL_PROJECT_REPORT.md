# AeroLogix Final Project Report

This report archives the 2026-11-15 Phase 2 review. Its status and limitations
are historical; the current implementation and validation evidence are in
[PHASE_3_IMPLEMENTATION_REPORT.md](PHASE_3_IMPLEMENTATION_REPORT.md).

**Review date:** 2026-11-15  
**Final status:** **READY WITH INFRASTRUCTURE LIMITATIONS**

The existing AeroLogix codebase is clean, documented and suitable for manual
GitHub review. Offline behavior, CSV validation, dbt parsing, Docker Compose
configuration, YAML and Markdown links were executed successfully. Live SQL
Server, warehouse, data-quality, dbt database operations and Airflow execution
remain unverified because those services are not available in the review
environment.

## 1. Project overview

AeroLogix is an educational airline operations and flight-intelligence platform
that moves deterministic fictional extracts through validated Python ingestion,
SQL Server OLTP, a dimensional warehouse, dbt transformations and an Airflow
orchestration definition.

## 2. Business problem

The platform demonstrates consistent route, flight, booking, delay and revenue
measures for operations analysis. It is not a dispatch, safety or production
airline reporting system.

## 3. Architecture

The seeded generator writes five CSV feeds. Python validates headers, types,
required values and business-key uniqueness, then stages and applies the feeds
transactionally. SQL Server contains `ref`, `ops`, `stg`, `dw`, `mart` and `etl`
schemas. dbt reads operational sources for staging and marts, while Airflow
coordinates ingestion and the warehouse procedure when separately deployed.

## 4. Technology stack

- Python 3.11+, pytest, pyodbc and python-dotenv
- SQL Server 2022 Developer, T-SQL and host `sqlcmd`
- Docker Compose for SQL Server only
- dbt Core with `dbt-sqlserver`
- Apache Airflow and Microsoft SQL Server provider as a separate deployment

## 5. Database architecture

OLTP tables model airports, aircraft, directed routes, passengers, flights,
bookings and maintenance events. Primary, foreign-key, unique and check
constraints enforce relational and domain rules. Warehouse dimensions use
surrogate keys; natural keys remain documented in
[DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## 6. Data ingestion workflow

1. Generate deterministic extracts with `aerologix.generate`.
2. Read all five feeds before opening the database transaction.
3. Normalize dates, timestamps, integers and decimal fares.
4. Reject schema drift, missing required values and duplicate source keys.
5. Replace staging rows and execute `etl.usp_ApplyOperationalLoad` in one
   transaction.
6. Roll back and close the connection on any failure.

## 7. Warehouse architecture

`DimDate`, `DimAirport`, `DimAircraft`, `DimRoute` and `DimPassenger` support
`FactFlight`, `FactBooking` and `FactDailyFlightSnapshot`. Fact grain is one
source FlightId, one source BookingId and one `(service date, FlightId)`
snapshot row respectively. Snapshot rows are current service-date aggregates,
not load-date history.

## 8. SCD implementations

- Airport: SCD Type 2 with current flag and validity interval.
- Aircraft: SCD Type 1 current attributes plus previous aircraft type (Type 3).
- Passenger loyalty: SCD Type 1.

Airport extracts have no authoritative effective timestamps, so historical
as-of attribution is explicitly limited.

## 9. dbt transformations

dbt contains two staging views, two marts, source definitions, generic tests
and an airport snapshot. The deprecated generic-test argument structures were
updated to the supported `arguments` form. Final `dbt parse` passed with no
deprecation warnings. Compile, test and run require a reachable SQL Server.

## 10. Airflow orchestration

The daily DAG has one Python ingestion task followed by a SQL Server warehouse
task. It configures three retries, a five-minute retry delay, a one-hour
execution timeout, `max_active_runs=1`, logging and an
`aerologix_sqlserver` connection. Airflow itself is separately deployed and
was not installed in the review environment.

## 11. Data-quality framework

`sql/analytics/data_quality.sql` produces a timestamped pass/fail report with
records checked and failed. It covers duplicate keys, orphan relationships,
required values, domains, dates, fares, aircraft capacity, dimension
resolution, fact uniqueness, SCD2 overlap and snapshot consistency.

## 12. Testing results

| Validation | Status | Evidence |
|---|---|---|
| Python compilation | PASS | `python -m compileall -q src tests scripts airflow/dags`, exit 0 |
| pytest | PASS | 9 passed, 1 skipped |
| unittest | PASS | 4 tests, 1 skipped; OK |
| CSV validation | PASS | 8 airports, 6 aircraft, 10 routes, 120 flights, 1,200 bookings |
| Generator repeatability | PASS | Checked-in pytest test passed |
| Docker Compose config | PASS | `docker compose config --quiet`, exit 0 with validation-only environment value |
| YAML validation | PASS | All 6 YAML files parsed |
| Markdown local links | PASS | All checked local links resolved |
| dbt parse | PASS | dbt 1.12.7; 4 models, 1 snapshot, 19 tests, 3 sources |
| SQL Server integration | BLOCKED | `localhost:1433` refused/timed out; no DSN configured |
| Warehouse loading | BLOCKED | Requires SQL Server |
| Data-quality execution | BLOCKED | Requires SQL Server |
| Airflow DAG import/execution | BLOCKED | Airflow package unavailable |

The complete Phase 2 evidence is in
[PHASE_2_VALIDATION_REPORT.md](PHASE_2_VALIDATION_REPORT.md).

## 13. Installation instructions

From the project directory:

```powershell
Copy-Item .env.example .env
# Set the same strong local password in SA_PASSWORD and SQLSERVER_PASSWORD.
docker compose up -d
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

Install Microsoft ODBC Driver 18 and `sqlcmd` on the host. Configure dbt using
`dbt/profiles.yml.example`. Install Airflow with matching constraints and its
SQL Server provider only in a dedicated Airflow environment.

## 14. Execution instructions

```powershell
python scripts/apply_sql.py
python -m aerologix.load --data data/raw --batch-size 1000
python scripts/load_warehouse.py
sqlcmd -C -S localhost,1433 -U sa -P "$env:SQLSERVER_PASSWORD" -b -i sql/analytics/data_quality.sql
```

For dbt, run from `dbt/`:

```powershell
dbt deps
dbt parse
dbt compile
dbt test
dbt run
```

## 15. Known limitations

- Live SQL Server and Airflow execution were not possible in this environment.
- Compose starts SQL Server only; Airflow and dbt are not provisioned there.
- SQL initialization is create-if-missing, not a versioned migration system.
- Airport source data lacks effective dates.
- No source feeds exist for crew, airline ownership or maintenance events.
- Invalid CSV rows are rejected, but no durable quarantine table exists.
- Existing databases may retain legacy objects; safe migration requires a
  separately reviewed migration process.

## 16. Future enhancements

Add versioned migrations, durable quarantine/replay, effective-dated airport
events, source-driven maintenance data, and sourced crew/airline entities only
when corresponding business data and rules are available. Add a CI job with
SQL Server and a separately constrained Airflow/dbt validation environment.

## 17. Final project status

**READY WITH INFRASTRUCTURE LIMITATIONS.** The code, documentation, tests and
available static/offline validations are complete. Manual approval still
requires running the exact SQL Server, warehouse, data-quality, dbt database and
Airflow checks listed in the closure checklist.
