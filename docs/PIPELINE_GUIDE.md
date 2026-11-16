# Pipeline guide

## Load sequence

1. Generate or inspect the five CSV extracts in `data/raw/`.
2. Run `python scripts/check_env.py` and `python scripts/upgrade_database.py`. The runner applies the repeatable create-if-missing baseline, creates a migration ledger, then applies each numbered migration once.
3. Run `python -m aerologix.load --data data/raw --batch-size 1000`. The loader validates all five files, explicitly maps snake_case headers, binds parameters, stages valid feeds, and invokes the OLTP upsert procedure within one transaction. Invalid rows are written to `data/quarantine/<execution-id>-<feed>.jsonl`; valid records continue. Header/schema errors still stop the feed because row mapping is unsafe.
4. Run `python scripts/load_warehouse.py` to execute `etl.usp_LoadWarehouse`.
5. Run `sql/analytics/data_quality.sql` for a timestamped quality report.

Each invocation emits structured JSON log lines with a UUID `execution_id`, source and rejected counts, duration and final status. `etl.PipelineRun` retains source/rejected/inserted/updated counts, per-feed counts, timestamps and failure details. Inserted/updated describe key existence before the upsert, not SQL row-level change detection. Do not log passwords or source-record payloads.

## Quarantine recovery

Review the JSONL rejection reason and correct the `record` fields while preserving the row's feed shape. Export the corrected records to CSV:

```powershell
python scripts/export_quarantine.py data/quarantine/<execution-id>-flights.csv.jsonl data/replay/flights.csv
```

Review the exported CSV and replace the corresponding rejected source rows in a complete feed (or in a copied five-feed input directory), then rerun the loader. Do not append a duplicate copy alongside the invalid original. Upserts key on source identifiers, so retrying a successfully loaded key does not create a duplicate. Keep quarantine and replay data local; they are excluded from Git.

## Database upgrades

`python scripts/upgrade_database.py` replays the existing idempotent baseline and then applies numbered `sql/migrations/NNN_*.sql` files once. Existing databases are upgraded in place; the initial ledger row marks the baseline after its create-if-missing scripts run. Migrations are forward-only: no automatic rollback is supplied. Back up the SQL Server volume/database before upgrades and write a reviewed compensating migration when a rollback is needed.

## Airflow

`airflow/dags/aerologix_daily.py` calls the same loader and warehouse procedure. Set `AEROLOGIX_PROJECT_DIR`, install `airflow/requirements.txt` using the official constraints file matching the Airflow/Python version, set loader environment variables (including SQL password), and create an Airflow SQL Server connection named `aerologix_sqlserver`. Put the DAG in the configured DAG folder. The project Compose file starts only SQL Server, not Airflow services.

## dbt

Install `dbt-sqlserver` compatible with the SQL Server version, copy `dbt/profiles.yml.example` to `dbt/profiles.yml`, configure credentials through environment variables, then from `dbt/` run `dbt deps`, `dbt parse`, `dbt snapshot`, `dbt run`, `dbt test`. dbt uses the `AeroLogix` database and reads operational source tables. The airport snapshot is independent from the warehouse SCD implementation.

