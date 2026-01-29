"""
Download Landsat imagery for urban growth analysis
Stores data locally in filesystem instead of S3
"""

import os
import requests
from datetime import datetime
import json
import shutil

DATA_DIR = os.getenv('DATA_DIR', '/opt/airflow/data')

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
    Stores locally in: data/urban-growth/{city}/{year}/{month}/
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
        
        # Create directory structure
        output_dir = os.path.join(DATA_DIR, 'urban-growth', city_name, str(year), f"{month:02d}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save file locally
        output_path = os.path.join(output_dir, 'imagery.tif')
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"✅ Downloaded and stored locally")
        print(f"   Path: {output_path}")
        print(f"   Size: {file_size:.2f} KB")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error downloading imagery: {e}")
        raise

def batch_download_for_city(city_name):
    """Download all time periods for a city"""
    city = load_city_config(city_name)
    
    downloaded = []
    for period in city['time_periods']:
        try:
            path = download_satellite_imagery(
                city_name, 
                period['year'], 
                period['month']
            )
            downloaded.append({
                'city': city_name,
                'year': period['year'],
                'month': period['month'],
                'path': path
            })
        except Exception as e:
            print(f"⚠️  Failed to download {city_name} {period['year']}: {e}")
    
    print(f"\n📊 Downloaded {len(downloaded)} scenes for {city_name}")
    return downloaded

if __name__ == "__main__":
    # Test run
    batch_download_for_city("Bangalore")