

# 🛰️ Automated Satellite GIS Platform

It is an end-to-end, containerized geospatial data pipeline. It automates the ingestion of satellite imagery (Raster data), stores it in a spatially-aware database, and prepares it for web-based visualization and environmental analysis.

## 🏗️ System Architecture

The platform is built on a modular Docker-based architecture:

* **Orchestration:** **Apache Airflow 2.8.0** handles the scheduling and workflow logic.
* **Spatial Database:** **PostGIS (Postgres 16 + PostGIS 3.4)** stores vector boundaries and raster tiles.
* **Object Storage:** **MinIO** acts as a local S3-compatible lake for raw `.tif` files.
* **GIS Engine:** A custom Airflow image pre-loaded with **GDAL**, **Rasterio**, and **Shapely** for heavy-duty spatial processing.
* **Visualization:** **GeoServer** connects to PostGIS to serve data via WMS/WFS protocols.

---

## 🚀 Quick Start (Rebuild Instructions)

To deploy a fresh instance of the platform:

### 1. Environment Setup

```bash
git clone https://github.com/cx4167/Automated-GIS-Satellite-Platform.git
cd Automated-GIS-Satellite-Platform/
mkdir -p dags src logs plugins

```

### 2. Permissions & Security

Ensure your local user and the Docker containers can communicate without ownership conflicts:

```bash
sudo chown -R $USER:$USER .
chmod -R 777 logs plugins

```

### 3. Build and Launch

```bash
docker-compose build --no-cache
docker-compose up -d

```

### 4. Initialize Spatial Extensions

Once the database is healthy, enable the spatial and raster engines:

```bash
docker-compose exec postgis psql -U gis_user -d gis_db -c "
  CREATE EXTENSION IF NOT EXISTS postgis;
  CREATE EXTENSION IF NOT EXISTS postgis_raster;
  CREATE ROLE airflow WITH LOGIN SUPERUSER PASSWORD 'dev_password';
"

```

---

## 🛠️ Lessons Learned & Troubleshooting

During development, we solved several critical infrastructure challenges:

* **The Dependency Gap:** Standard Airflow images do not include C-based GIS libraries. We solved this by creating a custom `Dockerfile.airflow` using a multi-stage build to compile `GDAL` dependencies.
* **Volume Ownership:** Docker-mounted volumes often create "Permission Denied" errors in Linux. We implemented a strategy of explicit `chown` and `chmod` calls to bridge the gap between the host OS and the containerized Airflow user (UID 50000).
* **The Ingestion Pivot:** Rather than relying on external CLI tools like `raster2pgsql` inside containers, we developed a **Pure-Python Ingestion Strategy** using `psycopg2` and memory-buffered streams (`io.BytesIO`) to push imagery directly into the DB.

---

## 📂 Project Structure

```text
.
├── dags/                # Airflow DAG definitions (Python)
├── src/                 # Custom GIS logic and processing scripts
├── logs/                # Airflow task logs (Git ignored)
├── docker-compose.yml   # Multi-container orchestration
├── Dockerfile.airflow   # Custom GIS-enabled Airflow image
└── .gitignore           # Prevents heavy imagery and secrets from being committed

```


