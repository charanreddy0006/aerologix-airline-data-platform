# Runbook and limitations

For prerequisites, startup and shutdown, see [SETUP_GUIDE.md](SETUP_GUIDE.md). For load order, Airflow and dbt see [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md).

The Compose stack provisions SQL Server only. Install ODBC Driver 18 and `sqlcmd` on the host; Airflow and dbt are separate deployments. Configure credentials with ignored `.env`, validate with `python scripts/check_env.py`, upgrade with `python scripts/upgrade_database.py`, load CSVs using `python -m aerologix.load`, and refresh the warehouse using `python scripts/load_warehouse.py`.

Use the structured `execution_id` from loader logs to inspect `etl.PipelineRun` and find matching local `data/quarantine/<execution-id>-*.jsonl` files. Correct records and follow [PIPELINE_GUIDE.md](PIPELINE_GUIDE.md#quarantine-recovery) before retrying. Quarantine files can contain source data and remain ignored by Git. Do not run write-enabled SQL integration scenarios outside an isolated disposable instance.

Inspect recent runs with `SELECT TOP (50) ExecutionId,StartedAt,FinishedAt,Status,SourceRecordCount,RejectedRecordCount,InsertedRecordCount,UpdatedRecordCount,DurationSeconds,FailureDetails FROM etl.PipelineRun ORDER BY StartedAt DESC;`. A `RUNNING` row with no finish time can indicate abrupt process/host termination. `AUDIT_FAILED` means the operational data transaction committed but its final audit update failed; investigate the error and retry safely. Validation failures before connecting to SQL Server appear in structured logs and quarantine but cannot be stored in the database audit table.

Before upgrades, take a database backup and verify the SQL Server container reports healthy. The named Docker volume persists local data across `docker compose down`; the volume is local persistence, not a backup. Periodically export a database backup to storage outside the container volume and test restore procedures. `docker compose down -v` permanently deletes the volume.

The data is fictional, seeded and limited to airport, aircraft, directed route, flight and booking feeds. Maintenance is modeled without a generated feed. There is no airline ownership or crew assignment source. Airport source rows do not carry effective timestamps, limiting historical SCD2 matching. The system is educational and not for dispatch, safety or actual operational decisions.
