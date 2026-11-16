# Airflow deployment

AeroLogix's Compose file runs SQL Server only. Run Airflow on Linux or WSL2 in a
separate virtual environment. Airflow 2.10.5 is constrained to Python 3.11;
install it with the official matching constraints file:

```bash
python3.11 -m venv .venv-airflow
source .venv-airflow/bin/activate
bash airflow/install_requirements.sh
```

Set `AEROLOGIX_PROJECT_DIR` to the absolute AeroLogix project path and export
the same SQL connection environment used by the loader, including
`SQLSERVER_PASSWORD`. Install this project into the Airflow environment with
`python -m pip install -e .`. Configure an Airflow connection with ID
`aerologix_sqlserver`, connection type Microsoft SQL Server, host/port/database
and credentials matching the database. Copy `airflow/dags/aerologix_daily.py`
into the configured DAG folder. The task first runs the validated loader, then
calls the idempotent warehouse procedure. Configure Airflow's metadata database
and executor according to the deployment environment; neither is provisioned by
this project.

The DAG has retries and execution timeouts. Inspect task logs using the emitted
`execution_id`, then query `etl.PipelineRun` for source/rejected/inserted/updated
counts, elapsed time, status and failure details. A retry replays the same
idempotent source keys.
