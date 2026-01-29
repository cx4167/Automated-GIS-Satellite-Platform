"""
GIS Platform Web Dashboard
Flask backend serving real-time data from PostGIS, MinIO, and Airflow
"""

from flask import Flask, render_template, jsonify
import psycopg2
import boto3
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ============================================================================
# DATABASE CONNECTIONS
# ============================================================================

def get_db_connection():
    """Connect to PostGIS database"""
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "gis_db"),
        user=os.getenv("POSTGRES_USER", "gis_user"),
        password=os.getenv("POSTGRES_PASSWORD", "dev_password"),
        host=os.getenv("POSTGRES_HOST", "postgis"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

def get_s3_client():
    """Connect to MinIO S3"""
    return boto3.client(
        's3',
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://minio:9000"),
        aws_access_key_id=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    )

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/urban-growth')
def urban_growth():
    """Urban growth analysis page"""
    return render_template('urban_growth.html')

@app.route('/maps')
def maps():
    """Interactive maps page"""
    return render_template('maps.html')

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/system-status')
def system_status():
    """Check health of all services"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'services': {}
    }
    
    # Check PostGIS
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        cur.close()
        conn.close()
        status['services']['postgis'] = {
            'status': 'healthy',
            'message': 'Connected'
        }
    except Exception as e:
        status['services']['postgis'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
    
    # Check MinIO
    try:
        s3 = get_s3_client()
        buckets = s3.list_buckets()
        status['services']['minio'] = {
            'status': 'healthy',
            'message': f"{len(buckets['Buckets'])} buckets"
        }
    except Exception as e:
        status['services']['minio'] = {
            'status': 'unhealthy',
            'message': str(e)
        }
    
    # Check Airflow
    try:
        airflow_url = os.getenv("AIRFLOW_URL", "http://airflow:8080")
        response = requests.get(f"{airflow_url}/health", timeout=5)
        status['services']['airflow'] = {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'message': 'API responding'
        }
    except Exception as e:
        status['services']['airflow'] = {
            'status': 'unknown',
            'message': str(e)
        }
    
    # Check GeoServer
    try:
        geoserver_url = os.getenv("GEOSERVER_URL", "http://geoserver:8080")
        response = requests.get(f"{geoserver_url}/geoserver/web/", timeout=5)
        status['services']['geoserver'] = {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'message': 'Web UI accessible'
        }
    except Exception as e:
        status['services']['geoserver'] = {
            'status': 'unknown',
            'message': str(e)
        }
    
    return jsonify(status)

@app.route('/api/data-inventory')
def data_inventory():
    """Get inventory of stored data"""
    inventory = {
        'local_files': [],
        'postgis_tables': [],
        'total_size': 0
    }
    
    # Get local files
    try:
        data_dir = os.getenv('DATA_DIR', '/app/data')
        if os.path.exists(data_dir):
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.endswith('.tif'):
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        rel_path = os.path.relpath(file_path, data_dir)
                        
                        inventory['local_files'].append({
                            'path': rel_path,
                            'size': file_size,
                            'modified': datetime.fromtimestamp(
                                os.path.getmtime(file_path)
                            ).isoformat()
                        })
                        inventory['total_size'] += file_size
    except Exception as e:
        print(f"Error getting file inventory: {e}")
    
    # Get PostGIS tables
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT table_name, 
                   pg_total_relation_size(quote_ident(table_name)::regclass) as size
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY size DESC;
        """)
        
        tables = cur.fetchall()
        for table in tables:
            # Get row count
            cur.execute(f"SELECT COUNT(*) FROM {table[0]};")
            count = cur.fetchone()[0]
            
            inventory['postgis_tables'].append({
                'name': table[0],
                'size': table[1],
                'rows': count
            })
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error getting PostGIS inventory: {e}")
    
    return jsonify(inventory)

@app.route('/api/urban-growth-metrics')
def urban_growth_metrics():
    """Get urban growth analysis results"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all metrics
        cur.execute("""
            SELECT city, year, month, urban_percentage, mean_ndvi, created_at
            FROM urban_growth_metrics
            ORDER BY city, year, month;
        """)
        
        metrics = []
        for row in cur.fetchall():
            metrics.append({
                'city': row[0],
                'year': row[1],
                'month': row[2],
                'urban_percentage': float(row[3]),
                'mean_ndvi': float(row[4]),
                'created_at': row[5].isoformat() if row[5] else None
            })
        
        # Get analysis results
        cur.execute("""
            SELECT city, start_year, end_year, growth_rate, 
                   annual_growth_rate, ndvi_change, analysis_date
            FROM urban_growth_analysis
            ORDER BY analysis_date DESC;
        """)
        
        analyses = []
        for row in cur.fetchall():
            analyses.append({
                'city': row[0],
                'start_year': row[1],
                'end_year': row[2],
                'growth_rate': float(row[3]),
                'annual_growth_rate': float(row[4]),
                'ndvi_change': float(row[5]),
                'analysis_date': row[6].isoformat() if row[6] else None
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            'metrics': metrics,
            'analyses': analyses
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-activities')
def recent_activities():
    """Get recent system activities"""
    activities = []
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get recent data additions
        cur.execute("""
            SELECT 'Urban Growth Metric' as type, 
                   city as description,
                   created_at as timestamp
            FROM urban_growth_metrics
            ORDER BY created_at DESC
            LIMIT 10;
        """)
        
        for row in cur.fetchall():
            activities.append({
                'type': row[0],
                'description': row[1],
                'timestamp': row[2].isoformat() if row[2] else None
            })
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error getting activities: {e}")
    
    return jsonify(activities)

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)