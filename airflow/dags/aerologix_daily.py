"""Daily, idempotent ingestion and warehouse refresh for AeroLogix."""
from datetime import datetime, timedelta
import logging
import os
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = os.getenv('AEROLOGIX_PROJECT_DIR', '/opt/aerologix')


def load_sources() -> None:
    """Run the validated loader against the configured synthetic source extracts."""
    LOGGER.info('Loading AeroLogix CSV feeds from %s', PROJECT_ROOT)
    environment = os.environ.copy()
    environment['PYTHONPATH'] = f'{PROJECT_ROOT}/src'
    subprocess.run(
        ['python', '-m', 'aerologix.load', '--data', f'{PROJECT_ROOT}/data/raw'],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        timeout=3600,
    )


DEFAULT_ARGS = {
    'owner': 'aerologix',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

with DAG(
    dag_id='aerologix_daily_pipeline',
    start_date=datetime(2025, 1, 1),
    schedule='0 5 * * *',
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=['aerologix', 'sqlserver'],
) as dag:
    ingest = PythonOperator(
        task_id='load_synthetic_source_extracts',
        python_callable=load_sources,
    )
    warehouse = SQLExecuteQueryOperator(
        task_id='load_dimensional_warehouse',
        conn_id='aerologix_sqlserver',
        sql='EXEC etl.usp_LoadWarehouse',
    )
    ingest >> warehouse
