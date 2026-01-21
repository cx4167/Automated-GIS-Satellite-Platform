import os
import boto3
import requests
import io
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Configuration
SAMPLE_TIFF_URL = "https://raw.githubusercontent.com/rasterio/rasterio/main/tests/data/RGB.byte.tif"
BUCKET_NAME = "raw-data"
OBJECT_NAME = "sentinel_2_sample.tif"

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("MINIO_ROOT_USER"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD")
    )

def ingest_data():
    print(f"⬇️  Step 1: Downloading sample GeoTIFF from External URL...")
    print(f"    Source: {SAMPLE_TIFF_URL}")
    
    try:
        # Stream the download so we don't eat up RAM
        response = requests.get(SAMPLE_TIFF_URL, stream=True)
        response.raise_for_status()
        
        # We use BytesIO to handle the file in memory
        file_data = io.BytesIO(response.content)
        file_size = file_data.getbuffer().nbytes
        print(f"✅ Download Complete. Size: {file_size / 1024:.2f} KB")

        print(f"⬆️  Step 2: Uploading to MinIO Data Lake...")
        s3 = get_s3_client()
        
        # Check if bucket exists, if not, create it (safety check)
        try:
            s3.head_bucket(Bucket=BUCKET_NAME)
        except ClientError:
            print(f"⚠️  Bucket '{BUCKET_NAME}' not found. Creating it...")
            s3.create_bucket(Bucket=BUCKET_NAME)

        # Upload
        s3.upload_fileobj(
            file_data, 
            BUCKET_NAME, 
            OBJECT_NAME,
            ExtraArgs={'ContentType': 'image/tiff'}
        )
        print(f"✅ Upload Success! Access it at: s3://{BUCKET_NAME}/{OBJECT_NAME}")

    except Exception as e:
        print(f"❌ Error during ingestion: {e}")

if __name__ == "__main__":
    ingest_data()