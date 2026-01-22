from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    'fetch_real_satellite_data',
    start_date=datetime(2023, 1, 1),
    schedule_interval="@weekly", # Automatically check every week
    catchup=False
) as dag:

    ingest_task = BashOperator(
        task_id='fetch_opentopo_data',
        bash_command='python3 /opt/airflow/src/ingest_real_data.py'
    )