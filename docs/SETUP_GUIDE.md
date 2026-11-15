# Local setup

## Prerequisites

- Windows, macOS or Linux with Docker Desktop/Engine and Compose plugin.
- Python 3.11 or newer and pip.
- Microsoft ODBC Driver 18 for SQL Server and `sqlcmd` on the host for Python loading and initialization.
- SQL Server Developer container uses local development credentials and certificate trust; do not reuse these settings in production.
- dbt and Airflow are optional and separately installed. Airflow requires its metadata database and version-matched constraints.

## Start and load

```powershell
Copy-Item .env.example .env
# Edit .env and set the same strong local password in SA_PASSWORD and SQLSERVER_PASSWORD.
docker compose up -d
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python scripts/apply_sql.py
python -m aerologix.load --data data/raw
python scripts/load_warehouse.py
```

On macOS/Linux activate with `source .venv/bin/activate`. Set `SQLSERVER_HOST`, `SQLSERVER_PORT`, `SQLSERVER_USER`, `SQLSERVER_PASSWORD`, and optionally `SQLSERVER_DATABASE` and `SQLSERVER_DRIVER`. Never commit `.env`.

Stop SQL Server with `docker compose down`; persistent database data remains in the named volume. `docker compose down -v` removes that local database volume.

