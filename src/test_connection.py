import psycopg2
import boto3
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connections():
    print("\n--- 🛰️  GIS Platform Connection Test ---\n")
    all_good = True

    # 1. Test PostGIS (Database)
    # We use the internal Docker DNS name 'postgis', not localhost
    print(f"Testing PostGIS connection to host: 'postgis'...")
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host="postgis", 
            port="5432"
        )
        print("✅ PostGIS: Connected successfully!")
        
        # Verify PostGIS extension is actually active
        cur = conn.cursor()
        cur.execute("SELECT PostGIS_Version();")
        version = cur.fetchone()[0]
        print(f"   └── PostGIS Version: {version}")
        conn.close()
    except Exception as e:
        print(f"❌ PostGIS: Connection failed. Error: {e}")
        all_good = False

    print("-" * 30)

    # 2. Test MinIO (S3 Storage)
    print(f"Testing MinIO connection to: '{os.getenv('S3_ENDPOINT_URL')}'...")
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
            aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
        )
        # Try to list buckets to prove auth works
        response = s3.list_buckets()
        print(f"✅ MinIO: Connected! Found {len(response['Buckets'])} buckets.")
    except Exception as e:
        print(f"❌ MinIO: Connection failed. Error: {e}")
        all_good = False

    print("\n" + "="*30)
    if all_good:
        print("🚀 SYSTEM READY FOR DEVELOPMENT")
    else:
        print("⚠️  SYSTEM HAS ISSUES")

if __name__ == "__main__":
    test_connections()