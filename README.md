# Automated GIS Satellite Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg)](#status)

A comprehensive, containerized geospatial platform for automated satellite imagery analysis, urban growth monitoring, and geospatial data management. Combines Apache Airflow for orchestration, PostGIS for spatial data storage, GeoServer for map services, and Flask for interactive visualizations.

## 🎯 Key Features

- **Automated Satellite Data Ingestion**: Fetch and process Landsat and optical satellite imagery with configurable scheduling
- **Urban Growth Analysis**: Track city expansion through automated NDVI calculations and change detection algorithms
- **Spatial Data Management**: Store and query geospatial data using PostGIS with Python ORM support
- **Workflow Orchestration**: Define and monitor multi-step GIS pipelines using Apache Airflow DAGs
- **Interactive Dashboard**: Real-time web interface for data visualization and system monitoring
- **Map Services**: WMS/WFS exposure of geospatial data through GeoServer
- **Scalable Architecture**: Fully containerized with Docker Compose for easy deployment
- **API-First Design**: RESTful endpoints for programmatic data access

## 🏗️ Architecture

The platform consists of five core microservices:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Web Dashboard (Flask)                       │
│                    :5005 - Interactive UI                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐ ┌─────────▼──────┐ ┌──────────▼────────┐
│   Airflow      │ │  GeoServer     │ │  PostGIS Database │
│   Scheduler    │ │  Map Services  │ │  Spatial Data     │
│   :8082        │ │  :8085         │ │  :5433            │
└────────────────┘ └────────────────┘ └───────────────────┘
        │                                       │
        └───────────────┬───────────────────────┘
                        │
        ┌───────────────▼──────────────┐
        │  GIS Processing Container    │
        │  (GDAL, Rasterio, GeoPandas) │
        └──────────────────────────────┘
```

### Service Details

| Service | Role | Port | Technology |
|---------|------|------|------------|
| **Dashboard** | Web interface & API gateway | 5005 | Flask, Leaflet.js |
| **Airflow** | Workflow orchestration & scheduling | 8082 | Apache Airflow 2.x |
| **PostGIS** | Spatial database backend | 5433 | PostgreSQL 16 + PostGIS 3.4 |
| **GeoServer** | Map tile & WMS services | 8085 | GeoServer 2.24 |
| **Processor** | GIS computation engine | — | GDAL, Python 3.11 |

## 📋 Prerequisites

- Docker & Docker Compose (v20.10+)
- 8GB RAM minimum (16GB recommended for large datasets)
- 50GB free disk space for satellite data
- OpenTopography API key (optional, for real Landsat data)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/cx4167/Automated-GIS-Satellite-Platform.git
cd Automated-GIS-Satellite-Platform
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Database credentials
POSTGRES_DB=gis_db
POSTGRES_USER=gis_user
POSTGRES_PASSWORD=your_secure_password

# API Keys
OPENTOPOGRAPHY_API_KEY=your_opentopography_key

# Service URLs (internal to Docker network)
AIRFLOW_URL=http://airflow:8080
GEOSERVER_URL=http://geoserver:8080
DATABASE_URL=postgresql://gis_user:your_secure_password@postgis:5432/gis_db
```

### 3. Start Services

```bash
docker-compose up -d
```

Monitor startup:

```bash
docker-compose logs -f
```

Expected startup time: 2-3 minutes

### 4. Verify Installation

```bash
# Check all services are healthy
docker-compose ps

# Test PostGIS connection
docker-compose exec postgis psql -U gis_user -d gis_db -c "SELECT version();"

# Access the dashboard
open http://localhost:5005
```

### 5. Access Web Interfaces

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Dashboard | http://localhost:5005 | N/A |
| Airflow | http://localhost:8082 | admin / airflow |
| GeoServer | http://localhost:8085 | admin / geoserver |
| PostGIS | localhost:5433 | gis_user / (your_password) |

## 📚 Usage

### Configure Urban Areas

Edit `config/urban_areas.json` to add or modify regions of interest:

```json
{
  "cities": [
    {
      "name": "Bangalore",
      "bbox": {
        "min_lon": 77.4,
        "min_lat": 12.8,
        "max_lon": 77.8,
        "max_lat": 13.2
      },
      "time_periods": [
        {"year": 2015, "month": 1},
        {"year": 2020, "month": 1},
        {"year": 2024, "month": 1}
      ]
    }
  ]
}
```

### Running Analysis Workflows

#### Via Airflow UI

1. Navigate to http://localhost:8082
2. Enable the desired DAG:
   - `urban_growth_tracking` - Monitor city expansion
   - `satellite_workflow` - Generic satellite data pipeline
   - `hello_world_gis` - Test connectivity

3. Click the play icon to trigger the DAG

#### Via Command Line

```bash
# Trigger a specific DAG
docker-compose exec airflow airflow dags trigger urban_growth_tracking

# List available DAGs
docker-compose exec airflow airflow dags list

# View task logs
docker-compose exec airflow airflow tasks logs urban_growth_tracking download_imagery 2024-01-01
```

### API Endpoints

The Flask dashboard exposes the following REST API:

#### System Health

```bash
curl http://localhost:5005/api/system-status
```

Response:

```json
{
  "timestamp": "2024-01-29T10:30:45.123456",
  "services": {
    "postgis": {"status": "healthy", "message": "Connected"},
    "airflow": {"status": "healthy", "message": "API responding"},
    "geoserver": {"status": "healthy", "message": "Web UI accessible"}
  }
}
```

#### Data Inventory

```bash
curl http://localhost:5005/api/data-inventory
```

Returns inventory of local GeoTIFF files and PostGIS table statistics.

#### Urban Growth Metrics

```bash
curl http://localhost:5005/api/urban-growth-metrics
```

Returns time-series urban expansion and NDVI data per city.

#### Recent Activities

```bash
curl http://localhost:5005/api/recent-activities
```

Returns feed of recent system operations.

## 📁 Project Structure

```
Automated-GIS-Satellite-Platform/
├── dags/                              # Airflow DAG definitions
│   ├── urban_growth_tracking.py       # Main urban monitoring pipeline
│   ├── satellite_workflow.py          # Generic satellite processing
│   ├── fetch_real_satellite.py        # Real data ingestion
│   └── hello_world_gis.py             # Test DAG
│
├── src/                               # Core GIS processing modules
│   ├── ingest_satellite.py            # Satellite data download logic
│   ├── ingest_real_data.py            # Real data ingestion utilities
│   ├── spatial_index.py               # PostGIS spatial indexing
│   ├── generate_mock_tif.py           # Test data generation
│   ├── test_connection.py             # Connectivity verification
│   └── urban_growth/                  # Urban analysis submodule
│       ├── download_landsat.py        # Landsat data fetching
│       ├── calculate_ndvi.py          # NDVI computation & storage
│       ├── detect_changes.py          # Change detection algorithms
│       └── visualize_growth.py        # Analysis visualization
│
├── frontend/                          # Flask web application
│   ├── app.py                         # Flask server & API routes
│   ├── requirements.txt               # Python dependencies
│   ├── Dockerfile                     # Container image definition
│   ├── static/
│   │   ├── css/style.css              # Dashboard styling
│   │   └── js/dashboard.js            # Frontend interactivity
│   └── templates/
│       ├── index.html                 # Main dashboard page
│       ├── urban_growth.html          # Growth analysis view
│       └── maps.html                  # Interactive map interface
│
├── config/                            # Configuration files
│   └── urban_areas.json               # City definitions & time periods
│
├── docker-compose.yml                 # Multi-container orchestration
├── Dockerfile                         # GIS processor container
├── Dockerfile.airflow                 # Airflow scheduler container
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment template
└── README.md                          # This file
```

## 🔧 Technologies Stack

### Geospatial Libraries
- **GDAL/OGR** - Raster and vector data handling
- **Rasterio** - Pythonic raster data interface
- **GeoPandas** - Spatial data frames
- **Shapely** - Geometric operations
- **Fiona** - Vector data I/O

### Backend Services
- **Apache Airflow 2.x** - Workflow orchestration
- **PostGIS** - Spatial database
- **GeoServer** - Web map services
- **Flask** - Web framework
- **SQLAlchemy** - ORM & connection pooling
- **psycopg2** - PostgreSQL adapter

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Python 3.11** - Runtime
- **PostgreSQL 16** - Database engine

## 🔐 Security Considerations

### Development vs. Production

**Current setup is development-grade.** For production:

1. **Database Credentials**: Store in a secrets manager (Vault, AWS Secrets Manager)
   ```bash
   # Change default passwords in docker-compose.yml
   POSTGRES_PASSWORD=${DB_PASSWORD}
   ```

2. **API Authentication**: Implement token-based auth (JWT/OAuth2)
   ```python
   # Add Flask-JWT-Extended to frontend/requirements.txt
   from flask_jwt_extended import create_access_token
   ```

3. **Network Isolation**: Use Docker networks instead of exposing ports
   ```yaml
   networks:
     gis_network:
       driver: bridge
   ```

4. **Environment Secrets**: Use `.env` file (never commit to version control)
   ```bash
   echo ".env" >> .gitignore
   ```

5. **Data Encryption**: Enable PostgreSQL SSL connections
   ```yaml
   environment:
     - PGSSLMODE=require
   ```

## 📊 Example Workflows

### Monitor Urban Growth in Bangalore

```bash
# Trigger the urban growth tracking DAG
curl -X POST http://localhost:8082/api/v1/dags/urban_growth_tracking/dagRuns \
  -H "Content-Type: application/json" \
  -d '{}'

# Monitor progress in Airflow UI
open http://localhost:8082

# Query results via API
curl http://localhost:5005/api/urban-growth-metrics | jq '.analyses[] | select(.city=="Bangalore")'
```

### Generate Test Data

```bash
# Create mock GeoTIFF files
docker-compose exec processor python src/generate_mock_tif.py

# Verify files
docker-compose exec processor ls -lh data/
```

### Access Satellite Data Programmatically

```python
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    dbname="gis_db",
    user="gis_user",
    password="dev_password",
    host="localhost",
    port="5433"
)

cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("SELECT * FROM urban_growth_metrics WHERE city = %s", ("Bangalore",))
results = cur.fetchall()

for row in results:
    print(f"{row['city']}: {row['urban_percentage']}% urbanized")

cur.close()
conn.close()
```

## 🧪 Testing

### Unit Tests

```bash
# Run tests on processor
docker-compose exec processor python -m pytest src/tests/ -v

# Test specific module
docker-compose exec processor python -m pytest src/tests/test_ndvi.py -v
```

### Integration Tests

```bash
# Verify database connectivity
docker-compose exec processor python src/test_connection.py

# Test end-to-end workflow
docker-compose exec processor python src/ingest_satellite.py --test
```

### Health Checks

```bash
# Automated health monitoring
curl http://localhost:5005/api/system-status | jq '.services[] | {service: .status}'

# Expected output:
# { "service": "healthy" }
# { "service": "healthy" }
# { "service": "healthy" }
```

## 📈 Performance Optimization

### Database Tuning

```sql
-- Create spatial indexes for faster queries
CREATE INDEX idx_urban_metrics_city ON urban_growth_metrics (city);
CREATE INDEX idx_urban_metrics_timestamp ON urban_growth_metrics (created_at);

-- Analyze table statistics
ANALYZE urban_growth_metrics;

-- Check index usage
SELECT * FROM pg_stat_user_indexes WHERE relname = 'urban_growth_metrics';
```

### Raster Processing

For large satellite datasets, optimize with:

```python
# Use tile-based processing
from rasterio.vrt import WarpedVRT

with WarpedVRT(src, resampling=Resampling.nearest) as vrt:
    # Process in chunks
    for chunk in vrt.block_windows(1):
        data = vrt.read(1, window=chunk[1])
```

### Airflow Optimization

```yaml
# Increase parallelism in docker-compose.yml
environment:
  - AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG=2
  - AIRFLOW__CORE__DAG_CONCURRENCY=5
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs for specific service
docker-compose logs airflow
docker-compose logs postgis
docker-compose logs dashboard

# Rebuild containers
docker-compose down
docker system prune -a
docker-compose up --build
```

### Database Connection Issues

```bash
# Verify database is ready
docker-compose exec postgis pg_isready -U gis_user

# Test connection manually
docker-compose exec postgis psql -U gis_user -d gis_db -c "SELECT 1;"
```

### Out of Memory

```bash
# Check container memory usage
docker stats

# Increase Docker memory allocation in Docker Desktop settings
# Then restart services:
docker-compose restart
```

### Airflow DAGs Not Appearing

```bash
# Ensure dags/ volume is mounted
docker-compose exec airflow ls -la /opt/airflow/dags/

# Restart scheduler
docker-compose restart airflow
```

## 📖 Additional Resources

- **Apache Airflow**: https://airflow.apache.org/docs/
- **PostGIS**: https://postgis.net/documentation/
- **GeoServer**: https://geoserver.org/
- **GDAL**: https://gdal.org/
- **Rasterio**: https://rasterio.readthedocs.io/

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## 🙌 Acknowledgments

- USGS for Landsat data availability
- OpenGeo for GeoServer and geospatial tools
- Apache Software Foundation for Airflow
- PostGIS community for spatial database support

## 📞 Support & Contact

For issues, feature requests, or questions:

- **GitHub Issues**: https://github.com/cx4167/Automated-GIS-Satellite-Platform/issues
- **Documentation**: See `docker-compose-installation.md` for detailed setup instructions

---

**Last Updated**: January 29, 2024
**Maintainer**: [Denish](https://github.com/cx4167)
