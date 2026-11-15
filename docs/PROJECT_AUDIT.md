# Project audit and findings

Audit scope: checked-in Python, SQL, dbt, Airflow, Docker, CSV, test and documentation assets. No SQL Server service or repository history is assumed.

| Severity | Finding | Affected files | Correction / status |
|---|---|---|---|
| Critical | Loader derived SQL columns with lowercase names; several CSV headers differ (`timezone`, `status`, `base_fare_usd`). | `src/aerologix/load.py` | Replaced with explicit feed mappings, strict header checks, duplicate-key checks, NULL handling, configurable batches, parameterized inserts and transactional rollback. |
| High | Loader did not validate all feeds before changing staging; it had no rollback/logging/close-on-error path. | `src/aerologix/load.py` | All five CSVs validate before connecting. Stage and apply share a transaction; failures roll back and connections close. |
| High | FactBooking MERGE refreshed only status/cabin/fare and left relationship and date keys stale after source corrections. | `sql/warehouse/02_load.sql` | MERGE now updates FlightId, date, passenger, airport, status, cabin and fare. |
| High | Daily snapshot inserted only missing keys and never refreshed changed status, booking count or revenue. | `sql/warehouse/02_load.sql` | Defined as a service-date snapshot and made repeat loads update each service-date/flight row. This is a current corrected aggregate, not a load-date history. |
| High | DDL could not be rerun safely because base tables and indexes were unguarded. | `sql/oltp/01_database.sql`, `02_staging.sql`, `sql/warehouse/01_warehouse.sql` | Table and index creation is guarded. Existing databases are not migrated by this create-if-missing approach. |
| Medium | Data generation had fixed seed/date/volume behavior, compressed implementation, and did not validate capacity input. | `src/aerologix/generate.py` | Added seed, date range, day span, counts, input validation, stable UTF-8 output, and clear CLI options. |
| Medium | Data quality SQL had only four coarse checks and no execution metadata or pass/fail report. | `sql/analytics/data_quality.sql` | Expanded into a timestamped report with checked/failed record counts and status covering source, referential, warehouse, SCD2 and snapshot rules. |
| Medium | Tests were unittest-only and loader behavior had no isolated coverage. | `tests/` | Added pytest tests for feed schema/NULLs/duplicates, explicit SQL mapping, batch behavior, commit/rollback/close, and generator options. SQL Server integration remains separately gated. |
| Medium | Architecture diagram described Airline and CrewMember entities absent from the source model; the warehouse crew bridge had no crew table or foreign keys. | `docs/architecture.md`, `sql/warehouse/01_warehouse.sql` | Diagrams now match supported entities. Removed the incomplete bridge from new initializations rather than representing an invalid relationship. No crew or airline entity was added without source data. |
| Medium | Docker provisions SQL Server only; README implied broader local environment. | `docker-compose.yml`, `README.md`, docs | Documented the actual SQL-only scope and separate Airflow/dbt prerequisites. Added `.env.example` already present and retained ignored `.env`. |
| Low | Airflow DAG had no task retry policy or execution timeout. | `airflow/dags/aerologix_daily.py` | Added retry delay, timeout, task logging, and connections/environment configuration guidance. |
| Low | dbt source/model tests and model documentation were sparse. | `dbt/models/`, docs | Added model tests/docs and clarified adapter/profile setup. dbt commands are not reported successful without environment verification. |

## Remaining architecture limitations

- The sample feed has no Airline or CrewMember data. Current SQL therefore models aircraft, routes, airports, passengers, flights, bookings and maintenance events. Adding airline/crew entities requires source data and business rules; no unsupported attributes are invented.
- Existing databases initialized before this change may still contain the unused `dw.BridgeFlightCrew` table. The repeatable initializer does not drop it; a versioned migration is needed to remove it safely. New initializations omit it.
- Airport SCD2 versions are retained and fact reruns preserve existing airport surrogate keys when the airport natural key is unchanged. The source extract has no effective timestamp, so initial fact assignments use the current version and cannot prove historical as-of attributes.
- The source extract is synthetic and does not produce maintenance events. Passenger identifiers are generated fictional tokens.
- SQL Server scripts use create-if-missing guards, not a versioned migration framework. They do not alter existing table definitions.
- Airflow is a deployable DAG definition, but Compose does not start Airflow or its metadata database.
- Quality checks are SQL reports; invalid source CSVs are rejected by the loader with row/file-specific errors. There is not yet a durable SQL quarantine table.

## Execution order

1. Start SQL Server and configure `.env`.
2. `python scripts/apply_sql.py` (OLTP, staging, logic, warehouse, warehouse load procedure).
3. `python -m aerologix.load --data data/raw` (validate and stage five CSV feeds, apply OLTP).
4. `python scripts/load_warehouse.py`.
5. Run `sql/analytics/data_quality.sql` with `sqlcmd` or SSMS.
6. Run dbt after configuring `dbt/profiles.yml`; use Airflow only after installing Airflow/provider dependencies and configuring its SQL Server connection.

