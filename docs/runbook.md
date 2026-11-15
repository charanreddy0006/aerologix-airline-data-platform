# Runbook and limitations

For prerequisites, startup and shutdown, see [SETUP_GUIDE.md](SETUP_GUIDE.md). For load order, Airflow and dbt see [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md).

The Compose stack provisions SQL Server only. Install ODBC Driver 18 and `sqlcmd` on the host; Airflow and dbt are separate deployments. Configure credentials with ignored `.env`, initialize scripts with `python scripts/apply_sql.py`, load CSVs using `python -m aerologix.load`, and refresh the warehouse using `python scripts/load_warehouse.py`.

The data is fictional, seeded and limited to airport, aircraft, directed route, flight and booking feeds. Maintenance is modeled without a generated feed. There is no airline ownership or crew assignment source. Airport source rows do not carry effective timestamps, limiting historical SCD2 matching. The system is educational and not for dispatch, safety or actual operational decisions.
