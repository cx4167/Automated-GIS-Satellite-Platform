"""
Calculate NDVI (Normalized Difference Vegetation Index)
Reads from local filesystem instead of S3
"""

import rasterio
import numpy as np
import os
import psycopg2

DATA_DIR = os.getenv('DATA_DIR', '/opt/airflow/data')

def calculate_ndvi_from_file(file_path):
    """
    Calculate NDVI from multi-band imagery stored locally
    
    Note: Real Landsat/Sentinel has NIR band (Band 5 for Landsat 8)
    For demo with RGB.byte.tif, we'll simulate NDVI using brightness
    """
    
    print(f"🔬 Calculating NDVI for: {file_path}")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with rasterio.open(file_path) as src:
        # For demo RGB file, simulate NDVI using red and green bands
        # In production: red = src.read(4), nir = src.read(5)
        red = src.read(1).astype(float)
        green = src.read(2).astype(float)  # Using green as NIR proxy
        
        # Calculate NDVI
        # Avoid division by zero
        denominator = (green + red)
        ndvi = np.where(
            denominator != 0,
            (green - red) / denominator,
            0
        )
        
        # Clip to valid NDVI range [-1, 1]
        ndvi = np.clip(ndvi, -1, 1)
        
        # Save NDVI result
        ndvi_path = file_path.replace('imagery.tif', 'ndvi.tif')
        
        profile = src.profile.copy()
        profile.update({
            'count': 1,
            'dtype': 'float32'
        })
        
        with rasterio.open(ndvi_path, 'w', **profile) as dst:
            dst.write(ndvi.astype('float32'), 1)
        
        # Calculate statistics
        urban_threshold = 0.2  # NDVI < 0.2 indicates urban areas
        urban_pixels = np.sum(ndvi < urban_threshold)
        total_pixels = ndvi.size
        urban_percentage = (urban_pixels / total_pixels) * 100
        
        print(f"✅ NDVI calculated:")
        print(f"   Urban area: {urban_percentage:.2f}%")
        print(f"   NDVI range: {ndvi.min():.3f} to {ndvi.max():.3f}")
        print(f"   Saved: {ndvi_path}")
        
        return {
            'ndvi_path': ndvi_path,
            'urban_percentage': urban_percentage,
            'mean_ndvi': float(np.mean(ndvi)),
            'stats': {
                'min': float(ndvi.min()),
                'max': float(ndvi.max()),
                'urban_pixels': int(urban_pixels),
                'total_pixels': int(total_pixels)
            }
        }

def store_ndvi_stats_in_db(city, year, month, stats):
    """Store NDVI statistics in PostGIS for time-series analysis"""
    
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "gis_db"),
        user=os.getenv("POSTGRES_USER", "gis_user"),
        password=os.getenv("POSTGRES_PASSWORD", "dev_password"),
        host=os.getenv("POSTGRES_HOST", "postgis"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )
    
    cur = conn.cursor()
    
    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS urban_growth_metrics (
            id SERIAL PRIMARY KEY,
            city VARCHAR(100),
            year INTEGER,
            month INTEGER,
            urban_percentage FLOAT,
            mean_ndvi FLOAT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Insert data
    cur.execute("""
        INSERT INTO urban_growth_metrics 
        (city, year, month, urban_percentage, mean_ndvi, file_path)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (city, year, month, stats['urban_percentage'], 
          stats['mean_ndvi'], stats['ndvi_path']))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"💾 Stored metrics in database")

def process_city_data(city_name):
    """Process all downloaded imagery for a city"""
    city_dir = os.path.join(DATA_DIR, 'urban-growth', city_name)
    
    if not os.path.exists(city_dir):
        print(f"⚠️  No data found for {city_name}")
        return
    
    processed = []
    
    # Walk through year/month directories
    for year in os.listdir(city_dir):
        year_path = os.path.join(city_dir, year)
        if not os.path.isdir(year_path):
            continue
            
        for month in os.listdir(year_path):
            month_path = os.path.join(year_path, month)
            imagery_path = os.path.join(month_path, 'imagery.tif')
            
            if os.path.exists(imagery_path):
                try:
                    print(f"\n📊 Processing {city_name} {year}/{month}")
                    stats = calculate_ndvi_from_file(imagery_path)
                    store_ndvi_stats_in_db(city_name, int(year), int(month), stats)
                    processed.append(stats)
                except Exception as e:
                    print(f"❌ Error processing {imagery_path}: {e}")
    
    print(f"\n✅ Processed {len(processed)} images for {city_name}")
    return processed

if __name__ == "__main__":
    # Test - process Bangalore data
    process_city_data("Bangalore")