from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Add /app/src to path so we can import your existing scripts
sys.path.append('/opt/airflow')
from src.ingest_satellite import ingest_data
from src.spatial_index import index_to_postgis

default_args = {
    'owner': 'geo_admin',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'satellite_ingestion_pipeline',
    default_args=default_args,
    description='Automated Satellite Download and PostGIS Indexing',
    schedule_interval=None, # Manual trigger for now
    catchup=False,
) as dag:

    # Task 1: Download from URL to MinIO
    download_task = PythonOperator(
        task_id='download_satellite_tif',
        python_callable=ingest_data,
    )

    # Task 2: Read from MinIO and Index to PostGIS
    index_task = PythonOperator(
        task_id='spatial_index_metadata',
        python_callable=index_to_postgis,
    )

    # Define the dependency
    download_task >> index_task