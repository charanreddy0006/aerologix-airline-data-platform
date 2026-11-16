# Testing and validation

## Offline checks

```powershell
python -m pip install -e . pytest
python -m compileall -q src tests scripts airflow/dags
python -m pytest -q
python -m unittest discover -s tests -v
```

The read-only SQL Server integration suite is skipped unless `AEROLOGIX_TEST_DSN` is set and `pyodbc` is installed. Point it only at a disposable, separately provisioned SQL Server instance/database seeded with the fixture counts. Never point it at a production or original project instance. The repository does not start or seed this isolated integration server automatically; that validation remains infrastructure-dependent.

The GitHub Actions workflow runs offline checks and does not require credentials. SQL Server and Airflow runtime validation are intentionally separate and are not inferred from CI green status.

## Infrastructure checks

```powershell
docker compose config
sqlcmd -C -S localhost,1433 -U sa -P "$env:SQLSERVER_PASSWORD" -b -i sql/analytics/data_quality.sql
cd dbt
dbt parse
dbt compile
```

dbt compile may require a configured profile/adapter; compilation does not prove a database connection. Docker, SQL Server, ODBC Driver 18, dbt adapter, and Airflow runtime availability must be checked on the machine executing these commands. Report blocked infrastructure checks as blocked rather than as passes.

