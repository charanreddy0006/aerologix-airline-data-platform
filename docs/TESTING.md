# Testing and validation

## Offline checks

```powershell
python -m pip install -e . pytest
python -m compileall -q src tests scripts airflow/dags
python -m pytest -q
python -m unittest discover -s tests -v
```

The SQL Server integration suite is skipped unless `AEROLOGIX_TEST_DSN` is set and `pyodbc` is installed. It expects a seeded database with the fixture counts represented in `tests/test_sqlserver_integration.py`.

## Infrastructure checks

```powershell
docker compose config
sqlcmd -C -S localhost,1433 -U sa -P "$env:SQLSERVER_PASSWORD" -b -i sql/analytics/data_quality.sql
cd dbt
dbt parse
dbt compile
```

dbt compile may require a configured profile/adapter; compilation does not prove a database connection. Docker, SQL Server, ODBC Driver 18, dbt adapter, and Airflow runtime availability must be checked on the machine executing these commands. Report blocked infrastructure checks as blocked rather than as passes.

