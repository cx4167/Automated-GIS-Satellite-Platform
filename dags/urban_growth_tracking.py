"""
Urban Growth Tracking Pipeline
Automated workflow for monitoring city expansion
Updated for local filesystem storage
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys

sys.path.append('/opt/airflow')

# Import the updated functions
from src.urban_growth.download_landsat import batch_download_for_city
from src.urban_growth.calculate_ndvi import process_city_data
from src.urban_growth.detect_changes import analyze_urban_growth

def download_bangalore_imagery():
    """Download all time periods for Bangalore"""
    return batch_download_for_city("Bangalore")

def process_bangalore_ndvi(**context):
    """Calculate NDVI for all downloaded imagery"""
    # Process all imagery for Bangalore
    result = process_city_data("Bangalore")
    return result

def analyze_bangalore_growth():
    """Run change detection analysis"""
    return analyze_urban_growth("Bangalore")

# DAG Configuration
default_args = {
    'owner': 'urban_planner',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'urban_growth_tracking',
    default_args=default_args,
    description='Track urban expansion using satellite imagery',
    schedule_interval='@monthly',  # Run monthly to check for new data
    catchup=False,
    tags=['gis', 'urban', 'monitoring'],
) as dag:

    # Task 1: Download satellite imagery
    download_task = PythonOperator(
        task_id='download_imagery',
        python_callable=download_bangalore_imagery,
    )

    # Task 2: Calculate NDVI
    ndvi_task = PythonOperator(
        task_id='calculate_ndvi',
        python_callable=process_bangalore_ndvi,
        provide_context=True,
    )

    # Task 3: Analyze growth patterns
    analysis_task = PythonOperator(
        task_id='analyze_growth',
        python_callable=analyze_bangalore_growth,
    )

    # Define workflow
    download_task >> ndvi_task >> analysis_task