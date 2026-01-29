# System Architecture

## Overview

The Automated GIS Satellite Platform is a modular, containerized geospatial data processing system designed for automated satellite imagery analysis, urban growth monitoring, and spatial data management.

## High-Level Architecture

```
External Data Sources
  ├── Landsat (via OpenTopography API)
  ├── USGS Earth Explorer
  └── Other Optical Sensors
         │
         ▼
┌─────────────────────────────────────────────────┐
│        Apache Airflow Orchestration Layer       │
│  - Scheduler: Triggers workflows on schedule    │
│  - Executor: Runs tasks in parallel/sequence    │
│  - UI: Monitor & manage DAGs at :8082           │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│    GIS Processing Container (GDAL Stack)        │
│  - Download satellite data                      │
│  - Clip to AOI (Area of Interest)               │
│  - Calculate spectral indices (NDVI, NDBI)      │
│  - Perform change detection                     │
│  - Generate visualizations                      │
└────────────┬────────────────────────────────────┘
             │
         ┌───┴──────────────────┐
         ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│   PostGIS DB     │   │   File Storage   │
│   (Spatial DB)   │   │   (GeoTIFFs)     │
│   - Raw vectors  │   │   - Raster data  │
│   - Metrics      │   │   - Archives     │
│   - Analysis     │   │   - Cache        │
└──────────────────┘   └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│         GeoServer (Web Services Layer)          │
│  - WMS (Web Map Service)                        │
│  - WFS (Web Feature Service)                    │
│  - TMS (Tile Map Service)                       │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│    Flask Dashboard (Presentation Layer)         │
│  - REST API endpoints                           │
│  - Interactive web UI                           │
│  - Real-time monitoring                         │
│  - Data export capabilities                     │
└─────────────────────────────────────────────────┘
             │
             ▼
        User Applications
        (Web Browser, Mobile, API Clients)
```

## Component Architecture

### 1. Data Ingestion Layer

**Responsibility**: Fetch and validate raw satellite data

**Components**:
- `dags/fetch_real_satellite.py` - Airflow DAG for automated downloads
- `src/ingest_satellite.py` - Satellite API integration
- `src/ingest_real_data.py` - Data validation & preprocessing
- `src/generate_mock_tif.py` - Test data generation

**Technologies**:
- OpenTopography API for Landsat access
- requests library for HTTP communication
- Rasterio for raster validation

**Data Flow**:
```
OpenTopography API
    ↓
ingest_satellite.py (fetch imagery)
    ↓
ingest_real_data.py (validate & organize)
    ↓
/app/data/ (local file storage)
```

### 2. Orchestration Layer (Airflow)

**Responsibility**: Schedule and coordinate GIS workflows

**Key DAGs**:

#### a) Urban Growth Tracking (`dags/urban_growth_tracking.py`)
```
download_imagery 
    ↓
calculate_ndvi
    ↓
analyze_growth
    ↓
store_results
```

Flow:
1. **Download Task**: Fetches multi-temporal Landsat scenes
2. **NDVI Task**: Calculates vegetation index from red/NIR bands
3. **Analysis Task**: Detects urban expansion through change detection

#### b) Satellite Workflow (`dags/satellite_workflow.py`)
Generic pipeline for arbitrary satellite data processing

#### c) Test DAG (`dags/hello_world_gis.py`)
Validates connectivity to all backend services

**Airflow Components**:
- **Scheduler**: Runs at container startup, checks DAGs every 60 seconds
- **Executor**: LocalExecutor (development) - tasks run sequentially on scheduler process
- **Metadata DB**: PostgreSQL backend (same as PostGIS)
- **UI**: Web server at port 8082

**Configuration**:
```python
# docker-compose.yml
environment:
  AIRFLOW__CORE__EXECUTOR=LocalExecutor
  AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://...
  AIRFLOW__CORE__LOAD_EXAMPLES=False
  
command: "airflow db migrate && (airflow scheduler & airflow webserver)"
```

### 3. GIS Processing Layer

**Responsibility**: Perform geospatial computations

**Modules**:

#### a) Download Module (`src/urban_growth/download_landsat.py`)
```python
def batch_download_for_city(city: str) -> List[Scene]:
    """
    Downloads multi-temporal satellite scenes for a city
    Returns: List of Scene objects with metadata
    """
```

**Process**:
1. Query `config/urban_areas.json` for city bounding box
2. For each time period, download scenes from OpenTopography
3. Store locally in `/app/data/{city}/{year}-{month}/`
4. Return scene metadata for downstream tasks

#### b) NDVI Calculation (`src/urban_growth/calculate_ndvi.py`)
```python
def calculate_ndvi_from_s3(s3_key: str) -> Dict[str, float]:
    """
    NDVI = (NIR - Red) / (NIR + Red)
    Measures vegetation health/density
    Returns: Statistics (mean, std, min, max)
    """
```

**Algorithm**:
```
Load Landsat bands:
  - Band 4 (Red): wavelength ~0.64 µm
  - Band 5 (NIR): wavelength ~0.87 µm

NDVI[pixel] = (NIR[pixel] - Red[pixel]) / (NIR[pixel] + Red[pixel])

Range: [-1, 1]
  - Negative/Low: Water, urban, bare soil
  - ~0.3-0.5: Sparse vegetation
  - 0.6+: Dense vegetation/forests

Store statistics in PostGIS:
  - Mean NDVI per scene
  - Spatial distribution
  - Temporal trends
```

#### c) Change Detection (`src/urban_growth/detect_changes.py`)
```python
def analyze_urban_growth(city: str) -> AnalysisResult:
    """
    Compares NDVI and built-up indices across time periods
    Identifies urban expansion patterns
    """
```

**Algorithm**:
```
For each city and time period pair:
  1. Calculate NDVI for T1 and T2
  2. Calculate NDBI (Normalized Difference Built-up Index)
     NDBI = (SWIR - NIR) / (SWIR + NIR)
  3. Threshold to identify urban pixels (NDBI > threshold)
  4. Calculate urbanization metrics:
     - Urban area (km²)
     - Urban percentage of AOI
     - Growth rate (% change)
  5. Store in urban_growth_analysis table
```

#### d) Visualization (`src/urban_growth/visualize_growth.py`)
Generates maps and charts for analysis results

### 4. Data Storage Layer

#### a) PostGIS (Spatial Database)

**Role**: Structured storage of vector data and metadata

**Key Tables**:

```sql
-- Urban growth metrics (time-series data)
CREATE TABLE urban_growth_metrics (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100),
    year INTEGER,
    month INTEGER,
    urban_percentage FLOAT,
    mean_ndvi FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Analysis results
CREATE TABLE urban_growth_analysis (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100),
    start_year INTEGER,
    end_year INTEGER,
    growth_rate FLOAT,
    annual_growth_rate FLOAT,
    ndvi_change FLOAT,
    analysis_date TIMESTAMP DEFAULT NOW()
);

-- Satellite scenes metadata
CREATE TABLE satellite_scenes (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100),
    scene_id VARCHAR(100) UNIQUE,
    acquisition_date DATE,
    cloud_cover FLOAT,
    bounds GEOMETRY(Polygon),
    data_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Spatial indexes
CREATE INDEX idx_urban_metrics_city ON urban_growth_metrics(city);
CREATE INDEX idx_urban_metrics_date ON urban_growth_metrics(year, month);
CREATE INDEX idx_satellite_bounds ON satellite_scenes USING GIST(bounds);
```

**Connection Pattern**:
```python
# SQLAlchemy with GeoAlchemy2
from geoalchemy2 import Geometry
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
# Supports spatial queries:
# session.query(SatelliteScene).filter(
#     SatelliteScene.bounds.contains(point)
# )
```

#### b) File Storage (GeoTIFF/NetCDF)

**Role**: Store raster imagery and processing artifacts

**Directory Structure**:
```
/app/data/
├── Bangalore/
│   ├── 2015-01/
│   │   ├── B4_Red.tif          (Raster bands)
│   │   ├── B5_NIR.tif
│   │   └── NDVI_2015-01.tif    (Derived products)
│   ├── 2020-01/
│   └── 2024-01/
├── Delhi/
└── ...
```

**File Format**: GeoTIFF
- Includes spatial reference (CRS)
- Geotransform (pixel-to-coordinate mapping)
- Multiple bands support
- Compression support (DEFLATE)

### 5. Map Services Layer (GeoServer)

**Responsibility**: Expose spatial data as standards-compliant web services

**Capabilities**:

#### WMS (Web Map Service)
```
http://geoserver:8080/geoserver/wms?
  SERVICE=WMS&VERSION=1.1.0&
  REQUEST=GetMap&
  LAYERS=gis_db:urban_growth_metrics&
  BBOX=77.4,12.8,77.8,13.2&
  WIDTH=500&HEIGHT=500&
  SRS=EPSG:4326&
  FORMAT=image/png
```

Returns: PNG/JPG map image for visualization

#### WFS (Web Feature Service)
```
http://geoserver:8080/geoserver/wfs?
  SERVICE=WFS&VERSION=2.0.0&
  REQUEST=GetFeature&
  TYPENAME=gis_db:satellite_scenes&
  OUTPUTFORMAT=application/json
```

Returns: GeoJSON with feature properties

#### REST API
```
GET /geoserver/rest/layers
GET /geoserver/rest/workspaces/gis_db/featuretypes
POST /geoserver/rest/data/stores
```

**Configuration**:
```yaml
# docker-compose.yml
geoserver:
  image: docker.osgeo.org/geoserver:2.24.0
  environment:
    - SKIP_DEMO_DATA=true
    - COMMUNITY_EXTENSIONS=pgraster-plugin
  depends_on:
    postgis: { condition: service_healthy }
```

### 6. API & Presentation Layer (Flask)

**Responsibility**: Provide RESTful interface and web dashboard

**Route Handlers** (`frontend/app.py`):

#### System Monitoring
```python
@app.route('/api/system-status')
def system_status():
    # Check health of: PostGIS, Airflow, GeoServer, MinIO
    # Returns: Status object with service states
```

#### Data Queries
```python
@app.route('/api/urban-growth-metrics')
def urban_growth_metrics():
    # Query PostGIS for time-series metrics
    # JOIN tables for complete analysis
    # Return: JSON with charts data
```

#### Data Inventory
```python
@app.route('/api/data-inventory')
def data_inventory():
    # List local GeoTIFF files
    # Query PostGIS table sizes
    # Calculate total storage
```

**Frontend** (`frontend/static/`):
- Leaflet.js: Interactive map rendering
- Chart.js: Time-series visualization
- D3.js: Advanced geospatial charts

## Data Flow Examples

### Example 1: Urban Growth Analysis Workflow

```
User triggers DAG via Airflow UI
    ↓
Airflow downloads Landsat scenes (2015, 2020, 2024)
    ↓
GIS processor clips to Bangalore bounding box
    ↓
Calculates NDVI for each scene:
  - Extract Red (B4) and NIR (B5) bands
  - Apply NDVI formula
  - Store statistics in PostGIS
    ↓
Change detection compares scenes:
  - 2015 vs 2020: Calculate growth rate
  - 2020 vs 2024: Calculate recent expansion
  - Identify urban pixels (NDBI threshold)
    ↓
Results stored in urban_growth_analysis table
    ↓
User views results in Flask dashboard
    ↓
GeoServer exposes data as WMS/WFS
```

### Example 2: Real-Time Dashboard Update

```
User opens Flask dashboard
    ↓
JavaScript calls /api/system-status
    ↓
Flask connects to PostGIS, Airflow, GeoServer
    ↓
Returns status JSON:
  {
    "postgis": "healthy",
    "airflow": "healthy",
    "geoserver": "healthy"
  }
    ↓
Dashboard renders status indicators
    ↓
JavaScript polls every 30 seconds
```

## Scaling Considerations

### Current Limitations (Single-Machine)

- **Airflow**: LocalExecutor runs tasks sequentially
- **Database**: Single PostGIS instance (no replication)
- **Storage**: Local filesystem (not distributed)
- **Processor**: Single container (limited by host CPU)

### Production Scaling Paths

#### Horizontal Scaling
```yaml
# Use CeleryExecutor for distributed tasks
airflow:
  environment:
    AIRFLOW__CORE__EXECUTOR=CeleryExecutor
  depends_on:
    - celery_worker_1
    - celery_worker_2
    - redis  # Message broker
```

#### Vertical Scaling
```yaml
# Use PostgreSQL replication
postgres_primary:
  image: postgis/postgis:16-3.4
  
postgres_replica:
  image: postgis/postgis:16-3.4
  environment:
    REPLICATE_FROM=postgres_primary
```

#### Cloud Deployment
```
AWS:
  - RDS for PostGIS (managed)
  - ECS for container orchestration
  - S3 for distributed storage
  - Lambda for serverless tasks

Google Cloud:
  - Cloud SQL for PostGIS
  - Cloud Run for Flask/Airflow
  - Cloud Storage for GeoTIFFs
```

## Security Architecture

### Current State (Development)

```
┌─────────────────────────────────────────┐
│  Public Internet (No Authentication)    │
│   :5005 Dashboard                       │
│   :8082 Airflow                         │
│   :8085 GeoServer                       │
│   :5433 PostGIS                         │
└──────────────┬──────────────────────────┘
               │
               ▼
        Docker bridge network
        (Internal communication)
```

### Production Architecture (Recommended)

```
┌──────────────────────────────────────────┐
│       HTTPS/TLS Encryption               │
│       API Gateway / Load Balancer        │
│       OAuth2 / JWT Authentication        │
└──────────────┬───────────────────────────┘
               │
        ┌──────┴───────┐
        ▼              ▼
  ┌──────────┐    ┌──────────┐
  │ Flask    │    │ Airflow  │
  │ (sealed) │    │ (sealed) │
  └────┬─────┘    └────┬─────┘
       │               │
       └───────┬───────┘
               ▼
    ┌─────────────────────────┐
    │ Private Docker Network  │
    │  - PostGIS              │
    │  - GeoServer            │
    │  - Processor            │
    │  - MinIO (optional)     │
    │                         │
    │  Encrypted connections  │
    └─────────────────────────┘
    
    └─ Vault: Manage secrets
    └─ IAM: Access control
    └─ Audit logging: Track access
```

## Performance Characteristics

### Current System (Development)

| Operation | Time | Bottleneck |
|-----------|------|-----------|
| Download 1 Landsat scene | 5-10 min | Network bandwidth |
| NDVI calculation (1 scene) | 2-5 min | CPU (GDAL processing) |
| Change detection (3 scenes) | 10-15 min | I/O (disk read/write) |
| PostGIS query (1 city) | <1 sec | Query optimization |
| Dashboard load | 2-3 sec | Network latency |

### Optimization Opportunities

1. **Data Processing**:
   - Use Dask for parallel raster processing
   - Implement tile-based processing for large datasets
   - Cache intermediate results

2. **Database**:
   - Add spatial indexes (GIST/BRIN)
   - Partition tables by time period
   - Archive old data to cold storage

3. **API**:
   - Implement response caching (Redis)
   - Lazy load data in dashboard
   - Paginate large result sets

## Error Handling & Resilience

### Airflow Task Failure Handling

```python
default_args = {
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
}

# Automatic retry on failure
# Manual retry via Airflow UI
# Dead letter queue for persistent failures
```

### Database Connection Resilience

```python
# Connection pooling with retries
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # Refresh every hour
    connect_args={'timeout': 10}
)
```

### Health Checks

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U gis_user"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Monitoring & Observability

### Available Metrics

1. **Airflow**: Task duration, DAG run history, scheduler logs
2. **PostGIS**: Query performance, table sizes, connection count
3. **Flask**: API response times, error rates, request logs
4. **System**: CPU, memory, disk I/O (via `docker stats`)

### Recommended Additions

```yaml
# Add Prometheus + Grafana for metrics
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  depends_on:
    - prometheus
```

## Conclusion

This architecture provides a modular, scalable foundation for geospatial data processing. Each layer has a clear responsibility, enabling independent scaling and technology upgrades without affecting the entire system.
