# Pipeline guide

## Load sequence

1. Generate or inspect the five CSV extracts in `data/raw/`.
2. Run `python scripts/apply_sql.py` once to initialize SQL Server in this order: OLTP database/tables, staging tables, OLTP view/procedure, warehouse tables, warehouse load procedure/views.
3. Run `python -m aerologix.load --data data/raw --batch-size 1000`. The loader validates all five files before connecting, explicitly maps snake_case headers, binds parameters, stages feeds, and invokes the OLTP upsert procedure within one transaction.
4. Run `python scripts/load_warehouse.py` to execute `etl.usp_LoadWarehouse`.
5. Run `sql/analytics/data_quality.sql` for a timestamped quality report.

## Airflow

`airflow/dags/aerologix_daily.py` calls the same loader and warehouse procedure. Set `AEROLOGIX_PROJECT_DIR`, install `airflow/requirements.txt` using the official constraints file matching the Airflow/Python version, set loader environment variables (including SQL password), and create an Airflow SQL Server connection named `aerologix_sqlserver`. Put the DAG in the configured DAG folder. The project Compose file starts only SQL Server, not Airflow services.

## dbt

Install `dbt-sqlserver` compatible with the SQL Server version, copy `dbt/profiles.yml.example` to `dbt/profiles.yml`, configure credentials through environment variables, then from `dbt/` run `dbt deps`, `dbt parse`, `dbt snapshot`, `dbt run`, `dbt test`. dbt uses the `AeroLogix` database and reads operational source tables. The airport snapshot is independent from the warehouse SCD implementation.

