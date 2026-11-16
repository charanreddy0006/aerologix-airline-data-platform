# Local setup

## Prerequisites

- Windows, macOS or Linux with Docker Desktop/Engine and Compose plugin.
- Python 3.11 or newer and pip.
- Microsoft ODBC Driver 18 for SQL Server and `sqlcmd` on the host for Python loading and initialization.
- SQL Server Developer container uses local development credentials and certificate trust; do not reuse these settings in production.
- Windows users should install Microsoft ODBC Driver 18 for SQL Server and the `sqlcmd` utility on the host; Docker's SQL Server tools are not automatically exposed to host Python.
- dbt and Airflow are optional and separately installed. Airflow requires its metadata database and version-matched constraints.

## Start and load

```powershell
Copy-Item .env.example .env
# Edit .env and set the same strong local password in SA_PASSWORD and SQLSERVER_PASSWORD.
docker compose up -d
docker compose ps
docker compose logs -f sqlserver
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python scripts/check_env.py
python scripts/upgrade_database.py
python -m aerologix.load --data data/raw
python scripts/load_warehouse.py
```

On macOS/Linux activate with `source .venv/bin/activate`. Set `SQLSERVER_HOST`, `SQLSERVER_PORT`, `SQLSERVER_USER`, `SQLSERVER_PASSWORD`, `SQLSERVER_DATABASE` and `SQLSERVER_DRIVER`. For the local Compose SQL Server using `sa`, keep `SQLSERVER_PASSWORD` equal to `SA_PASSWORD`. `docker compose up -d` waits asynchronously; use `docker compose ps` and wait for `healthy` before initializing. Never commit `.env`.

Stop SQL Server with `docker compose down`; persistent database data remains in the named `sqlserver_data` volume. `docker compose down -v` permanently removes that local database volume. ODBC Driver 18 encrypts connections by default; local configuration explicitly trusts the development server certificate. Use proper certificate validation outside local development.

