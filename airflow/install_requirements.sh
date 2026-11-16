#!/usr/bin/env bash
set -euo pipefail

AIRFLOW_VERSION="2.10.5"
PYTHON_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$PYTHON_MINOR" != "3.11" ]]; then
  echo "AeroLogix Airflow dependencies are constrained for Python 3.11; found $PYTHON_MINOR" >&2
  exit 2
fi
CONSTRAINTS="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_MINOR}.txt"
python -m pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "$CONSTRAINTS"
python -m pip install -r airflow/requirements.txt --constraint "$CONSTRAINTS"
