"""
Calculate NDVI (Normalized Difference Vegetation Index)
NDVI = (NIR - Red) / (NIR + Red)

High NDVI (0.6-0.9) = Dense vegetation
Medium NDVI (0.2-0.6) = Sparse vegetation
Low NDVI (-0.1-0.2) = Urban/Built areas
"""

import rasterio
import numpy as np
from rasterio.io import MemoryFile
import boto3
import os
import psycopg2

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
    )

def calculate_ndvi_from_s3(s3_key):
    """
    Calculate NDVI from multi-band imagery stored in S3
    
    Note: Real Landsat/Sentinel has NIR band (Band 5 for Landsat 8)
    For demo with RGB.byte.tif, we'll simulate NDVI using brightness
    """
    
    print(f"🔬 Calculating NDVI for: {s3_key}")
    
    s3 = get_s3_client()
    response = s3.get_object(Bucket="urban-growth", Key=s3_key)
    tiff_bytes = response['Body'].read()
    
    with MemoryFile(tiff_bytes) as memfile:
        with memfile.open() as src:
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
            
            # Create output file in memory
            profile = src.profile.copy()
            profile.update({
                'count': 1,
                'dtype': 'float32'
            })
            
            ndvi_memfile = MemoryFile()
            with ndvi_memfile.open(**profile) as dst:
                dst.write(ndvi.astype('float32'), 1)
            
            # Store NDVI result in S3
            ndvi_key = s3_key.replace('imagery.tif', 'ndvi.tif')
            ndvi_memfile.seek(0)
            
            s3.put_object(
                Bucket="urban-growth",
                Key=ndvi_key,
                Body=ndvi_memfile.read(),
                ContentType='image/tiff'
            )
            
            # Calculate statistics
            urban_threshold = 0.2  # NDVI < 0.2 indicates urban areas
            urban_pixels = np.sum(ndvi < urban_threshold)
            total_pixels = ndvi.size
            urban_percentage = (urban_pixels / total_pixels) * 100
            
            print(f"✅ NDVI calculated:")
            print(f"   Urban area: {urban_percentage:.2f}%")
            print(f"   NDVI range: {ndvi.min():.3f} to {ndvi.max():.3f}")
            print(f"   Stored: s3://urban-growth/{ndvi_key}")
            
            return {
                'ndvi_key': ndvi_key,
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
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="postgis"
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
            s3_ndvi_key TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Insert data
    cur.execute("""
        INSERT INTO urban_growth_metrics 
        (city, year, month, urban_percentage, mean_ndvi, s3_ndvi_key)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (city, year, month, stats['urban_percentage'], 
          stats['mean_ndvi'], stats['ndvi_key']))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"💾 Stored metrics in database")

if __name__ == "__main__":
    # Test
    result = calculate_ndvi_from_s3("Bangalore/2024/01/imagery.tif")
    store_ndvi_stats_in_db("Bangalore", 2024, 1, result)