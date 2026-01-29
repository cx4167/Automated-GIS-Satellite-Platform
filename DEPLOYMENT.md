# Deployment Guide

## Local Development Deployment

### Prerequisites

- Docker Desktop 4.0+
- Docker Compose 1.29+
- 8GB RAM, 50GB disk space
- Git

### Setup Steps

```bash
# 1. Clone repository
git clone https://github.com/cx4167/Automated-GIS-Satellite-Platform.git
cd Automated-GIS-Satellite-Platform

# 2. Create environment file
cat > .env << EOF
POSTGRES_DB=gis_db
POSTGRES_USER=gis_user
POSTGRES_PASSWORD=dev_password
OPENTOPOGRAPHY_API_KEY=your_api_key_here
EOF

# 3. Start services
docker-compose up -d

# 4. Verify all services are running
docker-compose ps

# 5. Check logs for any errors
docker-compose logs -f
```

### Verification Checklist

```bash
# PostGIS connectivity
docker-compose exec postgis psql -U gis_user -d gis_db -c "SELECT PostGIS_version();"

# Expected output:
# POSTGIS="3.4.0 3.4.0"

# Airflow scheduler
curl http://localhost:8082/health

# GeoServer
curl http://localhost:8085/geoserver/web/ | grep "<title>" | head -1

# Dashboard
curl http://localhost:5005/ | grep -o "<title>.*</title>"
```

## Docker Compose Reference

### Service Ports

| Service | Container Port | Host Port | Purpose |
|---------|----------------|-----------|---------|
| PostGIS | 5432 | 5433 | Database access |
| Airflow Web | 8080 | 8082 | UI & API |
| Airflow Scheduler | (internal) | — | DAG scheduling |
| GeoServer | 8080 | 8085 | Map services |
| Dashboard | 5000 | 5005 | Web UI & API |

### Useful Commands

```bash
# View logs for specific service
docker-compose logs -f postgis

# Execute command in container
docker-compose exec processor python src/test_connection.py

# Restart a service
docker-compose restart airflow

# Stop all services
docker-compose down

# Remove all data (reset everything)
docker-compose down -v

# View service status
docker-compose ps

# View resource usage
docker stats
```

## Production Deployment

### 1. Cloud Provider Setup

#### AWS EC2

```bash
# Launch Ubuntu 22.04 instance
# Instance type: t3.xlarge (4 CPU, 16GB RAM)
# Storage: 100GB gp3 EBS

# SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### Google Cloud Run

```bash
# Prerequisites
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create Cloud SQL instance for PostGIS
gcloud sql instances create gis-database \
  --database-version=POSTGRES_15 \
  --tier=db-custom-4-16384 \
  --region=us-central1

# Create database
gcloud sql databases create gis_db --instance=gis-database

# Create service account for access
gcloud iam service-accounts create gis-platform
```

#### Azure Container Instances

```bash
# Login to Azure
az login

# Create resource group
az group create --name gis-rg --location eastus

# Create container registry
az acr create --resource-group gis-rg \
  --name gisplatformregistry \
  --sku Basic

# Create PostgreSQL database
az postgres flexible-server create \
  --name gis-db-server \
  --resource-group gis-rg \
  --location eastus \
  --admin-user admin \
  --admin-password StrongPassword123!
```

### 2. Environment Configuration (Production)

Create `.env.production`:

```bash
# Database
POSTGRES_DB=gis_prod_db
POSTGRES_USER=gis_admin
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_HOST=gis-db.internal.company.com
POSTGRES_PORT=5432

# Airflow
AIRFLOW_SECRET_KEY=$(openssl rand -base64 32)
AIRFLOW__CORE__FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# API Keys
OPENTOPOGRAPHY_API_KEY=your_prod_api_key
USGS_EARTHEXPLORER_KEY=your_earthexplorer_key

# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$(openssl rand -base64 32)

# External Services
GEOSERVER_URL=https://maps.company.com/geoserver
AIRFLOW_URL=https://airflow.company.com
DASHBOARD_URL=https://gis.company.com

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=https://your_sentry_dsn
```

### 3. Docker Compose Production Override

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgis:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgis_data:/var/lib/postgresql/data
      - ./backup:/var/lib/postgresql/backup
    ports:
      - "5432:5432"  # Internal only - use VPN/SSH tunnel
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - gis_network
    
  processor:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_HOST: postgis
      OPENTOPOGRAPHY_API_KEY: ${OPENTOPOGRAPHY_API_KEY}
    volumes:
      - ./src:/app/src
      - gis_data:/app/data
    depends_on:
      postgis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - gis_network
    
  airflow:
    build:
      context: .
      dockerfile: Dockerfile.airflow
    environment:
      AIRFLOW_HOME: /opt/airflow
      AIRFLOW__CORE__DAGS_FOLDER: /opt/airflow/dags
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: ${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN}
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW__CORE__FERNET_KEY}
      AIRFLOW__CORE__LOAD_EXAMPLES: "False"
      AIRFLOW__CORE__PLUGINS_FOLDER: /opt/airflow/plugins
      PYTHONPATH: /opt/airflow
      POSTGRES_HOST: postgis
      OPENTOPOGRAPHY_API_KEY: ${OPENTOPOGRAPHY_API_KEY}
    volumes:
      - ./dags:/opt/airflow/dags
      - ./src:/opt/airflow/src
      - ./config:/opt/airflow/config
      - gis_data:/opt/airflow/data
      - airflow_logs:/opt/airflow/logs
    ports:
      - "8080:8080"
    command: bash -c "airflow db migrate && (airflow scheduler & airflow webserver --port 8080)"
    depends_on:
      postgis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - gis_network
    
  geoserver:
    image: docker.osgeo.org/geoserver:2.24.0
    environment:
      SKIP_DEMO_DATA: "true"
      INSTALL_EXTENSIONS: "true"
      COMMUNITY_EXTENSIONS: "pgraster-plugin"
      GEOSERVER_ADMIN_PASSWORD: ${GEOSERVER_ADMIN_PASSWORD}
    volumes:
      - geoserver_data:/opt/geoserver/data_dir
    ports:
      - "8085:8080"
    depends_on:
      postgis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - gis_network
    
  dashboard:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_HOST: postgis
      POSTGRES_PORT: 5432
      DATA_DIR: /app/data
      FLASK_ENV: production
      SECRET_KEY: ${SECRET_KEY}
    volumes:
      - ./frontend:/app
      - gis_data:/app/data
    ports:
      - "5000:5000"
    depends_on:
      postgis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - gis_network

volumes:
  postgis_data:
    driver: local
  geoserver_data:
    driver: local
  gis_data:
    driver: local
  airflow_logs:
    driver: local

networks:
  gis_network:
    driver: bridge
```

Deploy with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. Reverse Proxy Setup (Nginx)

Create `nginx.conf`:

```nginx
upstream flask_app {
    server dashboard:5000;
}

upstream airflow_app {
    server airflow:8080;
}

upstream geoserver_app {
    server geoserver:8080;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name gis.company.com airflow.company.com maps.company.com;
    return 301 https://$server_name$request_uri;
}

# Main dashboard
server {
    listen 443 ssl http2;
    server_name gis.company.com;
    
    ssl_certificate /etc/letsencrypt/live/gis.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gis.company.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}

# Airflow
server {
    listen 443 ssl http2;
    server_name airflow.company.com;
    
    ssl_certificate /etc/letsencrypt/live/airflow.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/airflow.company.com/privkey.pem;
    
    location / {
        auth_basic "Airflow";
        auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://airflow_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# GeoServer
server {
    listen 443 ssl http2;
    server_name maps.company.com;
    
    ssl_certificate /etc/letsencrypt/live/maps.company.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/maps.company.com/privkey.pem;
    
    location / {
        proxy_pass http://geoserver_app;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Deploy Nginx:

```bash
docker run -d \
  -p 80:80 -p 443:443 \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf \
  -v /etc/letsencrypt:/etc/letsencrypt \
  --network gis_network \
  nginx:latest
```

### 5. SSL/TLS Certificates (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificates
sudo certbot certonly --standalone \
  -d gis.company.com \
  -d airflow.company.com \
  -d maps.company.com

# Auto-renewal (runs twice daily)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### 6. Backup Strategy

Create `backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups/gis-platform"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

mkdir -p $BACKUP_DIR

# Backup PostGIS database
docker-compose exec -T postgis pg_dump -U gis_user gis_db | gzip > $DB_BACKUP

# Backup data files
tar -czf "$BACKUP_DIR/data_$TIMESTAMP.tar.gz" ./data/

# Backup GeoServer configuration
tar -czf "$BACKUP_DIR/geoserver_$TIMESTAMP.tar.gz" ./geoserver_data/

# Upload to cloud storage
aws s3 cp $DB_BACKUP s3://gis-backups/
aws s3 cp "$BACKUP_DIR/data_$TIMESTAMP.tar.gz" s3://gis-backups/
aws s3 cp "$BACKUP_DIR/geoserver_$TIMESTAMP.tar.gz" s3://gis-backups/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

Schedule with cron:

```bash
# Backup daily at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/gis-backup.log 2>&1
```

### 7. Monitoring & Logging

#### Prometheus + Grafana

```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus_data:/prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'

grafana:
  image: grafana/grafana:latest
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
  volumes:
    - grafana_data:/var/lib/grafana
    - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
  ports:
    - "3000:3000"
```

#### ELK Stack (Elasticsearch, Logstash, Kibana)

```yaml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
  environment:
    - discovery.type=single-node
    - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
  volumes:
    - elastic_data:/usr/share/elasticsearch/data

logstash:
  image: docker.elastic.co/logstash/logstash:8.0.0
  volumes:
    - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  depends_on:
    - elasticsearch

kibana:
  image: docker.elastic.co/kibana/kibana:8.0.0
  ports:
    - "5601:5601"
  depends_on:
    - elasticsearch
```

### 8. Scaling for Production

#### Using Kubernetes (Helm)

```bash
# Install Helm chart
helm repo add gis-platform https://charts.company.com
helm install gis-platform gis-platform/gis-platform \
  -f values-prod.yaml \
  --namespace gis-prod
```

`values-prod.yaml`:

```yaml
replicaCount: 3

airflow:
  executor: KubernetesExecutor
  workers: 3
  
postgis:
  persistence:
    size: 100Gi
  replication:
    enabled: true
    replicas: 2

geoserver:
  replicaCount: 2
  
dashboard:
  replicaCount: 2

ingress:
  enabled: true
  hosts:
    - gis.company.com
  tls:
    - hosts:
        - gis.company.com
      secretName: gis-tls
```

### 9. Health Checks & Monitoring

Create health check script:

```bash
#!/bin/bash

echo "GIS Platform Health Check - $(date)"

# Check PostGIS
if docker-compose exec -T postgis pg_isready -U gis_user > /dev/null 2>&1; then
    echo "✓ PostGIS: Healthy"
else
    echo "✗ PostGIS: Down"
    exit 1
fi

# Check Airflow
if curl -s http://localhost:8082/health | grep -q "healthy"; then
    echo "✓ Airflow: Healthy"
else
    echo "✗ Airflow: Down"
    exit 1
fi

# Check Dashboard
if curl -s http://localhost:5005/ > /dev/null; then
    echo "✓ Dashboard: Healthy"
else
    echo "✗ Dashboard: Down"
    exit 1
fi

# Check GeoServer
if curl -s http://localhost:8085/geoserver/web/ > /dev/null; then
    echo "✓ GeoServer: Healthy"
else
    echo "✗ GeoServer: Down"
    exit 1
fi

echo "All services healthy!"
```

Run daily:

```bash
0 */6 * * * /path/to/health-check.sh | mail -s "GIS Platform Health Check" ops@company.com
```

## Troubleshooting Production Deployments

### High Memory Usage

```bash
# Check memory limits
docker stats

# Reduce Airflow parallelism
environment:
  AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG: 1
  AIRFLOW__CORE__DAG_CONCURRENCY: 1
```

### Slow Database Queries

```bash
# Enable query logging
docker-compose exec postgis psql -U gis_user -d gis_db -c "
  ALTER SYSTEM SET log_min_duration_statement = 5000;
  SELECT pg_reload_conf();
"

# View slow logs
docker-compose exec postgis tail -f /var/log/postgresql/postgresql.log
```

### Certificate Renewal Issues

```bash
# Manual renewal
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal
```

## Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Database vacuum | Weekly | `VACUUM ANALYZE;` |
| Backup | Daily | `backup.sh` |
| Certificate renewal | Monthly | Automatic (certbot) |
| Log rotation | Daily | Automatic (Docker) |
| Security updates | Monthly | `apt update && apt upgrade` |
| Performance tuning | Quarterly | Review metrics |

---

For additional support, see [ARCHITECTURE.md](ARCHITECTURE.md) and the main [README.md](README.md).
