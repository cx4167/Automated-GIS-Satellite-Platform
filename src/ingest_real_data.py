import os
import requests
import psycopg2
import io
import rasterio
from rasterio.io import MemoryFile

# Config
API_KEY = os.getenv("OPENTOPOGRAPHY_API_KEY")
DB_PARAMS = {"dbname": "gis_db", "user": "gis_user", "password": "dev_password", "host": "postgis", "port": "5432"}

def download_and_upload():
    params = {
        'demtype': 'SRTMGL1', 'south': 27.9, 'north': 28.0, 'west': 86.9, 'east': 87.0,
        'outputFormat': 'GTiff', 'API_Key': API_KEY
    }
    url = "https://portal.opentopography.org/API/globaldem"
    
    try:
        response = requests.get(url, params=params, timeout=60)
        if response.status_code == 200:
            print("✅ Downloaded GeoTIFF. Converting to PostGIS format...")
            
            # Use rasterio to ensure the file is valid before sending to DB
            with MemoryFile(response.content) as memfile:
                with memfile.open() as dataset:
                    print(f"📦 Raster Info: {dataset.width}x{dataset.height}, Bands: {dataset.count}")
            
            # Connect and Upload
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            try:
                cur.execute("CREATE TABLE IF NOT EXISTS real_elevation (rid serial primary key, rast raster);")
                
                # We use the ST_FromGDALRaster but we explicitly tell Postgres it is a TIFF
                # by passing the bytes through a hex format that PostGIS prefers
                print("💾 Ingesting into PostGIS...")
                cur.execute(
                    "INSERT INTO real_elevation (rast) VALUES (ST_FromGDALRaster(%s));",
                    (response.content,)
                )
                conn.commit()
                print("🎉 SUCCESS: Real-world elevation data stored!")
            except Exception as db_error:
                print(f"❌ DB Error: {db_error}")
            finally:
                cur.close()
                conn.close()
        else:
            print(f"❌ API Error: {response.status_code}")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    download_and_upload()