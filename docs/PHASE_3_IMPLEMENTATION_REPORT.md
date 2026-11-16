# AeroLogix Phase 3 Implementation Report

**Review date:** 2026-11-16  
**Branch:** `phase-3/reliability-automation`  
**Status:** **READY WITH INFRASTRUCTURE LIMITATIONS**

Phase 3 reliability changes are implemented in the existing project. Changes
remain local on the feature branch; no commit or push was made. This report
records local checks only and does not claim that the new GitHub workflow or
SQL Server integration suite has run on GitHub.

## Changes delivered

| Area | Implementation | Why it matters |
|---|---|---|
| Local setup | `scripts/check_env.py` validates required credentials, matching local `sa` passwords and SQL port. Compose validates `SA_PASSWORD`, maps a configurable host port, health-checks SQL Server and retains its named data volume. | Fails early on configuration errors and makes startup/readiness and persistence clear. |
| Database upgrades | `scripts/upgrade_database.py` bootstraps older databases with the idempotent baseline, then applies numbered SQL migrations once under a SQL Server application lock. Migration `001_pipeline_audit.sql` creates the pipeline audit table. | Existing databases get an additive upgrade path; subsequent runs do not replay baseline DDL. |
| Pipeline telemetry | Loader logs JSON with an execution UUID, feed, counts, duration and status. `etl.PipelineRun` stores run timestamps, accepted/rejected counts, per-feed counts, estimated inserted/updated counts and failure details. | Supports failure investigation and retry correlation. |
| Quarantine | Invalid rows are written to ignored local JSONL files with the original row and reason; valid records continue. Header/schema drift stops safely. `scripts/export_quarantine.py` exports manually corrected rows for review. | Rejections are retained for correction and replay rather than silently dropped. |
| dbt | Added source not-null/unique and accepted-value coverage plus singular tests for flight summary and booking revenue grains and business rules. | Validates source contracts and aggregate model grain. |
| Airflow | Added a Python 3.11/Airflow 2.10.5 official-constraints installer and separate deployment notes. Existing task retries, timeout and SQL Server connection boundary remain. | Makes the separate deployment reproducible and easier to configure. |
| CI | `.github/workflows/ci.yml` separates offline validation from a disposable SQL Server service job. The latter initializes/upgrades twice, reloads data and warehouse twice, runs SQL quality checks, and gates write-enabled constraint/SCD checks to that ephemeral service. | Automates repeatability checks without production credentials. |
| Documentation | Updated setup, pipeline, runbook, README, testing and historical report pointers. | Describes implemented behavior and keeps Phase 2 evidence clearly historical. |

### Main files

- Created: `.github/workflows/ci.yml`, `scripts/check_env.py`,
  `scripts/upgrade_database.py`, `scripts/export_quarantine.py`,
  `scripts/validate_docs.py`, `sql/migrations/001_pipeline_audit.sql`,
  `dbt/tests/assert_flight_summary_grain.sql`,
  `dbt/tests/assert_booking_revenue_grain.sql`, `airflow/README.md`,
  `airflow/install_requirements.sh`, and this report.
- Modified: `src/aerologix/load.py`, `scripts/apply_sql.py`,
  `tests/test_loader.py`, `tests/test_project.py`,
  `tests/test_sqlserver_integration.py`, `dbt/models/sources.yml`,
  `dbt/models/marts/schema.yml`, `docker-compose.yml`, `.env.example`,
  `.gitignore`, `README.md`, and the setup, testing, runbook, pipeline, and
  historical report documentation.

## How to run locally

From the repository root on Windows with Docker Desktop:

```powershell
Copy-Item .env.example .env
# Replace the example password; keep SA_PASSWORD and SQLSERVER_PASSWORD equal for local sa.
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python scripts/check_env.py
docker compose up -d
docker compose ps
python scripts/upgrade_database.py
python -m aerologix.load --data data/raw --batch-size 1000
python scripts/load_warehouse.py
```

Install Microsoft ODBC Driver 18 and `sqlcmd` on the host. See
[SETUP_GUIDE.md](SETUP_GUIDE.md), [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md),
[runbook.md](runbook.md), and [Airflow deployment notes](../airflow/README.md).
Use `docker compose down` to stop the SQL Server container while keeping its
volume. `docker compose down -v` deletes that local volume.

For a corrected rejected record, edit its JSONL `record`, export it with
`python scripts/export_quarantine.py <execution-id>-<feed>.csv.jsonl <feed>.csv`,
review it, replace the corresponding bad row in a complete input feed, then rerun
the loader. Do not append a duplicate of the invalid source row.

## Local validation evidence

| Check | Status | Evidence |
|---|---|---|
| Python compilation | PASS | `python -m compileall -q src tests scripts airflow/dags` exited 0. |
| pytest | PASS | `13 passed, 3 skipped`; the three SQL Server integration cases require a DSN. |
| unittest | PASS | 8 tests discovered; 5 passed and 3 SQL Server integration cases skipped. |
| Dataset validation | PASS | Existing tests read all five checked-in feeds and verify expected counts/relationships. |
| YAML parse | PASS | All project YAML files parse; see the local command evidence in this review. |
| Docker Compose config | PASS | `docker compose config --quiet` exited 0 with a validation-only `SA_PASSWORD`; Docker printed a warning that the user Docker config was inaccessible. |
| dbt parse | PASS | dbt Core 1.12.7 and SQL Server adapter 1.12.2 parsed with the example profile and a placeholder password; no live connection was made. |
| Markdown links | PASS | `scripts/validate_docs.py` resolves local links across README and docs. |
| GitHub Actions execution | NOT TESTED | The workflow is configured but was not run on GitHub from this environment. |
| SQL Server service integration | BLOCKED | No local disposable SQL Server was available. The new workflow provisions one without external credentials. |
| SQL data quality execution | BLOCKED | Requires the SQL Server integration service or another disposable SQL Server. |
| Airflow import/scheduler execution | NOT TESTED | Airflow is separately deployable and is not installed in this environment. |

The integration tests check seeded row counts, migration count, flight snapshot
consistency, check/foreign-key/primary-key/unique constraints, transaction
rollback, and airport SCD Type 2 behavior. Write scenarios require
`AEROLOGIX_TEST_WRITES=1`; only the CI job's disposable SQL Server sets it.

## Operational notes and limitations

- `etl.PipelineRun` audits the Python ingestion attempt. Airflow task state and
  warehouse procedure failures remain visible in Airflow task logs; they are
  not currently written as a second audit stage in that table.
- Inserted/updated counts are key-existence estimates captured before upsert,
  not row-level `MERGE OUTPUT` change counts. They include matched keys even
  when values did not change.
- A feed validation failure before SQL connection is recorded in structured
  logs and quarantine where available, but cannot create a database audit row.
- `AUDIT_FAILED` means the source transaction committed but final audit status
  persistence failed. The load remains safe to retry because source keys are
  upserted.
- Quarantine is local JSONL without centralized access control or retention;
  operators must protect and clean it according to their data-handling policy.
- Migrations are forward-only. Back up the database/volume before upgrading;
  use reviewed compensating migrations for rollback.
- The SQL Server Developer container and local certificate trust are for
  development and isolated CI only, not production deployment.
- CI uses a SQL Server 2022 service container and installs ODBC Driver 18. Its
  first execution is still pending, so no integration result is claimed.

## Remaining technical debt

- Add a warehouse-load audit stage linked to Airflow's run ID if operational
  reporting needs a single end-to-end record.
- Replace estimated upsert counters with explicit insert/update counts from SQL
  procedure output if exact row-change metrics are needed.
- Centralize quarantine only when retention, access-control and replay
  requirements justify the additional infrastructure.
- Validate CI on GitHub and review its service-container result before treating
  the SQL integration suite as passed.
befor