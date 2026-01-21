import os
import boto3
import rasterio
from rasterio.io import MemoryFile
from shapely.geometry import box
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_s3_data():
    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
    )
    # Get the file we just uploaded
    response = s3.get_object(Bucket="raw-data", Key="sentinel_2_sample.tif")
    return response['Body'].read()

def index_to_postgis():
    print("📖 Reading metadata from MinIO...")
    tiff_bytes = get_s3_data()

    # Use Rasterio to 'look' at the file in memory
    with MemoryFile(tiff_bytes) as memfile:
        with memfile.open() as dataset:
            bounds = dataset.bounds
            crs = dataset.crs.to_string()
            width = dataset.width
            height = dataset.height
            
            # Create a geometric box (footprint)
            geom = box(*bounds)
            wkt_geom = geom.wkt # Well-Known Text format for SQL

    print(f"📍 Found Footprint: {bounds}")
    print(f"🌐 CRS: {crs}")

    # Connect to PostGIS to store this info
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host="postgis"
        )
        cur = conn.cursor()

        # 1. Ensure the table exists with a Geometry column
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS satellite_inventory (
                id SERIAL PRIMARY KEY,
                file_name TEXT,
                crs TEXT,
                footprint GEOMETRY(Polygon, 32618) -- Matches the sample file's UTM zone
            );
        """)

        # 2. Insert the metadata
        insert_query = """
            INSERT INTO satellite_inventory (file_name, crs, footprint)
            VALUES (%s, %s, ST_GeomFromText(%s, 32618));
        """
        cur.execute(insert_query, ("sentinel_2_sample.tif", crs, wkt_geom))
        
        conn.commit()
        print("✅ Success: Metadata and Footprint saved to PostGIS!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    index_to_postgis()