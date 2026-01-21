from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG('hello_world_gis', start_date=datetime(2023, 1, 1), schedule_interval=None, catchup=False) as dag:
    
    # Since the Python script now does BOTH creation and upload
    run_ingest = BashOperator(
        task_id='generate_and_upload',
        bash_command='python3 /opt/airflow/src/generate_mock_tif.py'
    )