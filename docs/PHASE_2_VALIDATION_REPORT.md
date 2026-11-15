# AeroLogix Phase 2 Validation Report

**Validation timestamp:** 2026-11-15T21:01:37+05:30  
**Environment:** Windows, Python 3.11.9, SQLCMD with Microsoft ODBC Driver 18  
**Scope:** Existing AeroLogix codebase; no GitHub operations or project recreation

## Executive summary

The offline Python and project checks passed. A fresh synthetic dataset was generated
in an isolated session directory and all five feeds passed the loader's schema,
type, null and duplicate-key validation.

Live SQL Server validation was **BLOCKED**. No SQL Server container or local instance
was available, no `.env` or `AEROLOGIX_TEST_DSN` was configured, and the connection
probe to `localhost,1433` failed with a TCP connection error. Consequently, no
database-writing or SQL Server-dependent result is represented as a pass.

dbt dependencies were installable. `dbt parse` passed; database-dependent dbt
commands were blocked by the same unavailable SQL Server endpoint. Airflow was not
installed, so only Python compilation of the DAG was performed.

**Closure update (2026-11-15):** The six deprecated dbt generic-test argument
blocks reported below were migrated to the supported `arguments` structure.
`dbt parse --no-partial-parse` was rerun successfully with no deprecation
warnings.

## Status definitions

- **PASS:** Executed successfully and evidence was collected.
- **FAIL:** Executed and produced a product or test failure.
- **BLOCKED:** Could not execute because required infrastructure or dependency was unavailable.
- **NOT TESTED:** Not executed.

## 1. SQL Server initialization and relational validation

| Test | Status | Evidence |
|---|---|---|
| OLTP database/schema initialization | BLOCKED | `scripts/apply_sql.py` could not run without `SQLSERVER_PASSWORD`; the SQL Server probe to `localhost,1433` failed with ODBC `08001`, TCP error `10061` and “target machine actively refused it”. |
| Staging tables | BLOCKED | Requires SQL Server execution. |
| Warehouse tables | BLOCKED | Requires SQL Server execution. |
| Stored procedures and views | BLOCKED | Requires SQL Server execution. |
| Data-quality SQL | BLOCKED | Requires SQL Server execution and populated tables. |
| Primary keys | BLOCKED | No live database available for insert/rejection tests. |
| Foreign keys | BLOCKED | No live database available for insert/rejection tests. |
| Unique constraints | BLOCKED | No live database available for insert/rejection tests. |
| Check constraints | BLOCKED | No live database available for insert/rejection tests. |
| Index existence | BLOCKED | No live database available for catalog queries. |
| Repeatable script execution | BLOCKED | No live database available for first or second execution. |

The checked-in script order in `scripts/apply_sql.py` is:
`01_database.sql`, `02_staging.sql`, `03_logic.sql`, `warehouse/01_warehouse.sql`,
`warehouse/02_load.sql`. This ordering was reviewed but not executed.

## 2. Python ingestion validation

| Test | Status | Evidence |
|---|---|---|
| Synthetic generation | PASS | Generated 120 flights and 10 bookings per flight into an isolated session directory using seed `8212026`. |
| CSV schema/type/null validation | PASS | `aerologix.load.read_feed` successfully read all five feeds. Cancelled-flight `actual_departure` nulls were preserved: 3 rows. |
| CSV record counts | PASS | Airports 8; Aircraft 6; Routes 10; Flights 120; Bookings 1,200. |
| Duplicate source keys | PASS | Flight IDs unique; booking IDs unique; booking references unique. |
| SQL Server ingestion | BLOCKED | Requires SQL Server and a configured password/DSN. |
| CSV-to-SQL record comparison | BLOCKED | No SQL Server counts available. |
| Live rollback test | BLOCKED | No SQL Server transaction available. |
| Offline rollback behavior | PASS | `test_loader_rolls_back_and_closes_after_failure` passed using an isolated controlled failure; rollback and close were asserted. |

The checked-in loader tests also passed for explicit column mappings, required
value rejection, duplicate-key rejection and nullable timestamp handling.

## 3. Data warehouse validation

| Test | Status | Evidence |
|---|---|---|
| Dimension loading | BLOCKED | Requires SQL Server. |
| FactFlight loading | BLOCKED | Requires SQL Server. |
| FactBooking loading | BLOCKED | Requires SQL Server. |
| FactDailyFlightSnapshot loading | BLOCKED | Requires SQL Server. |
| Surrogate-key relationships | BLOCKED | Requires warehouse queries. |
| Airport SCD Type 2 | BLOCKED | No controlled source update was run against SQL Server. |
| Aircraft SCD Type 1/3 | BLOCKED | No controlled source update was run against SQL Server. |
| Passenger SCD Type 1 | BLOCKED | No controlled source update was run against SQL Server. |
| Idempotent warehouse rerun | BLOCKED | Neither the first nor second warehouse load could run. |
| Duplicate fact/snapshot comparison | BLOCKED | No warehouse result sets available. |

## 4. Data-quality validation

| Test | Status | Evidence |
|---|---|---|
| Execute `sql/analytics/data_quality.sql` | BLOCKED | SQL Server unavailable. |
| Produce SQL quality report | BLOCKED | No SQL result set or execution timestamp available. |
| Controlled invalid-record detection | BLOCKED | No isolated SQL Server test database available. |

The SQL quality script defines checks for duplicate keys, orphan relationships,
invalid domains, nulls, capacity, warehouse dimension resolution, SCD2 overlap,
fact uniqueness and snapshot consistency. These are source-reviewed only and were
not reported as executed results.

## 5. dbt validation

| Command | Status | Evidence |
|---|---|---|
| Install dbt dependencies | PASS | Installed `dbt-sqlserver 1.12.2`, `dbt-core 1.12.7`, and `pyodbc 5.5.0`. `packages.yml` contains no external packages. |
| `dbt debug` | BLOCKED | Profile loaded and project configuration was valid, but connection failed because `localhost:1433` refused the connection. |
| `dbt parse` | PASS | Phase 2 parsed 4 models, 1 snapshot, 19 data tests, 3 sources and 578 macros. The six deprecation warnings were resolved during closure; the final `dbt parse --no-partial-parse` completed with no deprecation warnings. |
| `dbt compile` | BLOCKED | Database connection failed with ODBC `08001` / TCP `10061` after the project parsed. |
| `dbt test` | BLOCKED | Database connection failed with ODBC `08001` / TCP `10061`. |
| `dbt run` | BLOCKED | Database connection failed with ODBC `08001` / TCP `10061`. |

The example profile was copied only to the session workspace for validation; no
credential was written to the project.

## 6. Airflow validation

| Test | Status | Evidence |
|---|---|---|
| Python dependency availability | BLOCKED | `airflow` executable/package was not installed. |
| DAG source compilation | PASS | `python -m compileall -q src tests scripts airflow/dags` exited 0. |
| DAG import/task graph | BLOCKED | Airflow package unavailable, so the DAG was not imported or rendered. |
| SQL Server connectivity | BLOCKED | No SQL Server endpoint. |
| Retry/failure/logging behavior | NOT TESTED | Requires Airflow execution or a test scheduler. |
| Idempotency | BLOCKED | Requires live ingestion and warehouse execution. |
| DAG execution | BLOCKED | Airflow and SQL Server unavailable. |

## 7. End-to-end validation

| Stage | Status | Evidence |
|---|---|---|
| Synthetic data generation | PASS | Isolated five-feed dataset generated. |
| CSV validation | PASS | All five feeds parsed and validated; counts were 8/6/10/120/1,200. |
| SQL Server ingestion | BLOCKED | SQL Server unavailable. |
| Staging/OLTP processing | BLOCKED | SQL Server unavailable. |
| Warehouse loading | BLOCKED | SQL Server unavailable. |
| dbt transformations | BLOCKED | SQL Server unavailable for compilation/execution. |
| Data-quality execution | BLOCKED | SQL Server unavailable. |

## 8. Offline regression results

Commands executed from the project root:

```text
python -m compileall -q src tests scripts airflow/dags
  exit code: 0

python -m pytest -q
  9 passed, 1 skipped in 0.31s

python -m unittest discover -s tests -v
  4 tests, 1 skipped; OK
```

The skipped test was `SqlServerIntegration.test_load_populates_coherent_grains`,
which requires `AEROLOGIX_TEST_DSN` and `pyodbc`.

## Remaining issues and prerequisites

1. Provide a running isolated SQL Server 2022 instance or start the project
   Compose service with a strong `SA_PASSWORD`.
2. Configure `SQLSERVER_PASSWORD` (or `AEROLOGIX_TEST_DSN`) and rerun the SQL,
   ingestion, warehouse, quality and integration checks.
3. Install/configure Airflow with the project's compatible constraints and
   `aerologix_sqlserver` connection before claiming DAG execution.
4. No dbt generic-test deprecation warnings remain after the closure update.
5. After SQL Server is available, execute the controlled constraint, rollback,
   SCD and two-run idempotency scenarios and append their actual result sets here.

No live SQL Server, warehouse, data-quality, Airflow, or end-to-end result is
claimed as successful in this report.
