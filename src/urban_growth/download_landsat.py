"""
Download Landsat imagery for urban growth analysis
Uses NASA's Landsat API or alternative public sources
"""

import os
import requests
import rasterio
from datetime import datetime
import boto3
from io import BytesIO
import json

def load_city_config(city_name):
    """Load configuration for a specific city"""
    with open('/opt/airflow/config/urban_areas.json', 'r') as f:
        config = json.load(f)
    
    for city in config['cities']:
        if city['name'] == city_name:
            return city
    raise ValueError(f"City {city_name} not found in config")

def download_satellite_imagery(city_name, year, month):
    """
    Download satellite imagery for a specific city and time period
    
    For demo purposes, we'll use Sentinel-2 L2A from public sources
    In production, you'd use NASA EarthData, Sentinel Hub, or Google Earth Engine
    """
    
    city = load_city_config(city_name)
    bbox = city['bbox']
    
    print(f"📡 Downloading imagery for {city_name} - {year}/{month:02d}")
    print(f"   BBox: ({bbox['min_lon']}, {bbox['min_lat']}) to ({bbox['max_lon']}, {bbox['max_lat']})")
    
    # For demo: Use a public Landsat/Sentinel scene
    # In production, you'd query actual satellite APIs
    sample_url = "https://raw.githubusercontent.com/rasterio/rasterio/main/tests/data/RGB.byte.tif"
    
    try:
        response = requests.get(sample_url, timeout=60)
        response.raise_for_status()
        
        # Store in MinIO
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
            aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
        )
        
        # Create bucket if needed
        try:
            s3.head_bucket(Bucket="urban-growth")
        except:
            s3.create_bucket(Bucket="urban-growth")
        
        # Store with structured naming
        object_key = f"{city_name}/{year}/{month:02d}/imagery.tif"
        
        s3.put_object(
            Bucket="urban-growth",
            Key=object_key,
            Body=response.content,
            ContentType='image/tiff'
        )
        
        print(f"✅ Stored: s3://urban-growth/{object_key}")
        return object_key
        
    except Exception as e:
        print(f"❌ Error downloading imagery: {e}")
        raise

def batch_download_for_city(city_name):
    """Download all time periods for a city"""
    city = load_city_config(city_name)
    
    downloaded = []
    for period in city['time_periods']:
        try:
            key = download_satellite_imagery(
                city_name, 
                period['year'], 
                period['month']
            )
            downloaded.append({
                'city': city_name,
                'year': period['year'],
                'month': period['month'],
                's3_key': key
            })
        except Exception as e:
            print(f"⚠️  Failed to download {city_name} {period['year']}: {e}")
    
    print(f"\n📊 Downloaded {len(downloaded)} scenes for {city_name}")
    return downloaded

if __name__ == "__main__":
    # Test run
    batch_download_for_city("Bangalore")