import rasterio
from rasterio.transform import from_origin
import numpy as np
import psycopg2
import io

# Database connection
DB_PARAMS = {
    "dbname": "gis_db",
    "user": "gis_user",
    "password": "dev_password",
    "host": "postgis",
    "port": "5432"
}

def create_and_upload():
    # 1. Create the Mock Data in Memory (No file permission issues!)
    data = np.ones((1, 100, 100), dtype=rasterio.uint8) * 100
    transform = from_origin(0, 0, 0.01, 0.01)
    
    # Save to a memory buffer instead of a file on disk
    mem_file = io.BytesIO()
    with rasterio.open(
        mem_file, 'w', driver='GTiff',
        height=data.shape[1], width=data.shape[2],
        count=1, dtype=data.dtype,
        crs='EPSG:4326', transform=transform
    ) as dst:
        dst.write(data)
    
    # Reset buffer to start
    mem_file.seek(0)
    hex_data = mem_file.read().hex() # Convert binary to hex for SQL

    # 2. Upload to PostGIS using Python
    # We use ST_FromGDALRaster to convert the TIF bytes into a DB raster
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        
        # Create table if not exists
        cur.execute("CREATE TABLE IF NOT EXISTS mock_forest (rid serial primary key, rast raster);")
        
        # Insert the data
        print("Uploading raster to database...")
        # PostGIS accepts HexWKB, so we pass the hex string of the TIF
        # This is a simplified way to ingest without raster2pgsql
        cur.execute(
            "INSERT INTO mock_forest (rast) VALUES (ST_FromGDALRaster('\x" + hex_data + "'::bytea));"
        )
        
        conn.commit()
        cur.close()
        conn.close()
        print("SUCCESS: Mock forest uploaded to PostGIS!")
        
    except Exception as e:
        print(f"Database Error: {e}")
        raise e

if __name__ == "__main__":
    create_and_upload()