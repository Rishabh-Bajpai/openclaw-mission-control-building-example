# Deployment Guide

Complete guide for deploying OpenClaw Mission Control to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Option 1: Docker Deployment](#option-1-docker-deployment-recommended)
- [Option 2: Traditional VPS](#option-2-traditional-vps)
- [Option 3: Cloud Platforms](#option-3-cloud-platforms)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying, ensure you have:

- [ ] OpenClaw Gateway running and accessible
- [ ] Domain name configured (optional but recommended)
- [ ] Server/VPS with at least 2GB RAM
- [ ] PostgreSQL database (for production)
- [ ] SSL certificate (Let's Encrypt recommended)

## Architecture

Production deployment involves multiple components:

```
┌─────────────────────────────────────────┐
│              Nginx (Reverse Proxy)     │
│              SSL/TLS Termination         │
└─────────────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
┌──────────────┐      ┌──────────────┐
│   Frontend   │      │   Backend    │
│   (Next.js)   │      │  (FastAPI)   │
│   Port 3000  │      │   Port 8002  │
└──────────────┘      └──────┬───────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
            ┌──────────────┐  ┌──────────────┐
            │  PostgreSQL  │  │  Redis       │
            │   Database   │  │   (Cache)    │
            └──────────────┘  └──────────────┘
                    │
                    ▼
            ┌──────────────┐
            │OpenClaw      │
            │Gateway       │
            └──────────────┘
```

## Option 1: Docker Deployment (Recommended)

### Step 1: Create Dockerfile

**backend/Dockerfile**:

```dockerfile
# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

**frontend/Dockerfile**:

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy built application
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Expose port
EXPOSE 3000

# Set environment
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run application
CMD ["node", "server.js"]
```

### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  # Database
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mission_control
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mission_control

  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${POSTGRES_PASSWORD:-changeme}@postgres:5432/mission_control
      OPENCLAW_GATEWAY_URL: ${OPENCLAW_GATEWAY_URL}
      OPENCLAW_GATEWAY_TOKEN: ${OPENCLAW_GATEWAY_TOKEN}
      LLM_API_URL: ${LLM_API_URL:-https://api.openai.com/v1/chat/completions}
      LLM_API_KEY: ${LLM_API_KEY}
      DEBUG: "false"
      HOST: "0.0.0.0"
      PORT: "8002"
    ports:
      - "8002:8002"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - mission_control
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://localhost:8002}
    ports:
      - "3000:3000"
    depends_on:
      - backend
    networks:
      - mission_control
    restart: unless-stopped

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - certbot-data:/etc/letsencrypt
      - certbot-www:/var/www/certbot
    depends_on:
      - frontend
      - backend
    networks:
      - mission_control
    restart: unless-stopped

volumes:
  postgres_data:
  certbot-data:
  certbot-www:

networks:
  mission_control:
    driver: bridge
```

### Step 3: Configure Environment

**Create .env file**:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password_here

# OpenClaw Gateway
OPENCLAW_GATEWAY_URL=ws://your-openclaw-server:18789
OPENCLAW_GATEWAY_TOKEN=your_openclaw_token_here

# LLM API
LLM_API_KEY=your_llm_api_key_here
LLM_API_URL=https://api.openai.com/v1/chat/completions

# Frontend
NEXT_PUBLIC_API_URL=https://your-domain.com/api
```

### Step 4: Deploy

```bash
# Clone repository
git clone https://github.com/Rishabh-Bajpai/openclaw-mission-control-building-example.git
cd openclaw-mission-control

# Create environment file
cp .env.example .env
# Edit .env with your values

# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Step 5: Database Migrations

```bash
# Run migrations inside container
docker-compose exec backend alembic upgrade head

# Or manually create tables
docker-compose exec backend python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
```

## Option 2: Traditional VPS

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv nodejs npm nginx postgresql redis-server

# Create user
sudo useradd -m -s /bin/bash missioncontrol
sudo usermod -aG sudo missioncontrol
```

### Step 2: PostgreSQL Setup

```bash
# Login as postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE mission_control;
CREATE USER mcuser WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE mission_control TO mcuser;
\q

# Configure pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
# Add: host mission_control mcuser 127.0.0.1/32 scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 3: Backend Deployment

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/Rishabh-Bajpai/openclaw-mission-control-building-example.git
sudo chown -R missioncontrol:missioncontrol openclaw-mission-control

# Setup backend
cd openclaw-mission-control/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create environment file
sudo nano /opt/openclaw-mission-control/backend/.env
```

**Backend .env**:

```bash
DATABASE_URL=postgresql+asyncpg://mcuser:your_password@localhost:5432/mission_control
OPENCLAW_GATEWAY_URL=ws://your-openclaw-server:18789
OPENCLAW_GATEWAY_TOKEN=your_token_here
LLM_API_KEY=your_key_here
DEBUG=false
```

```bash
# Test backend
uvicorn app.main:app --host 0.0.0.0 --port 8002

# Create systemd service
sudo nano /etc/systemd/system/missioncontrol-backend.service
```

**Backend service**:

```ini
[Unit]
Description=Mission Control Backend
After=network.target postgresql.service

[Service]
Type=simple
User=missioncontrol
WorkingDirectory=/opt/openclaw-mission-control/backend
Environment=PATH=/opt/openclaw-mission-control/backend/venv/bin
ExecStart=/opt/openclaw-mission-control/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8002
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl daemon-reload
sudo systemctl enable missioncontrol-backend
sudo systemctl start missioncontrol-backend
sudo systemctl status missioncontrol-backend
```

### Step 4: Frontend Deployment

```bash
# Setup frontend
cd /opt/openclaw-mission-control/frontend
npm ci

# Create environment
sudo nano /opt/openclaw-mission-control/frontend/.env.local
```

**Frontend .env.local**:

```bash
NEXT_PUBLIC_API_URL=http://your-server-ip:8002
```

```bash
# Build
npm run build

# Install PM2
sudo npm install -g pm2

# Create ecosystem file
sudo nano /opt/openclaw-mission-control/ecosystem.config.js
```

**ecosystem.config.js**:

```javascript
module.exports = {
  apps: [
    {
      name: 'missioncontrol-frontend',
      cwd: '/opt/openclaw-mission-control/frontend',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G'
    }
  ]
};
```

```bash
# Start frontend
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

### Step 5: Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/missioncontrol
```

**Nginx config**:

```nginx
upstream backend {
    server 127.0.0.1:8002;
}

upstream frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    # API
    location /api/ {
        proxy_pass http://backend/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API docs
    location /docs {
        proxy_pass http://backend/docs;
    }
    
    location /openapi.json {
        proxy_pass http://backend/openapi.json;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/missioncontrol /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Option 3: Cloud Platforms

### AWS ECS (Elastic Container Service)

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name mission-control

# Create task definition
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Run service
aws ecs create-service \
    --cluster mission-control \
    --service-name mission-control-service \
    --task-definition mission-control \
    --desired-count 2 \
    --launch-type FARGATE
```

**ecs-task-definition.json**:

```json
{
  "family": "mission-control",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "your-registry/missioncontrol-backend:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8002,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql+asyncpg://..."
        }
      ],
      "secrets": [
        {
          "name": "OPENCLAW_GATEWAY_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mission-control",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      }
    }
  ]
}
```

### Heroku

```bash
# Login
heroku login

# Create app
heroku create missioncontrol-prod

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Set environment variables
heroku config:set OPENCLAW_GATEWAY_URL=ws://...
heroku config:set OPENCLAW_GATEWAY_TOKEN=...
heroku config:set LLM_API_KEY=...

# Deploy
git push heroku main

# Scale
heroku ps:scale web=1
```

**Procfile**:

```
web: uvicorn app.main:app --host=0.0.0.0 --port=${PORT:-8002}
```

### Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
railway init

# Add PostgreSQL
railway add --database postgres

# Set environment variables
railway variables set OPENCLAW_GATEWAY_URL=ws://...
railway variables set OPENCLAW_GATEWAY_TOKEN=...

# Deploy
railway up
```

## SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal test
sudo certbot renew --dry-run

# Restart nginx
sudo systemctl restart nginx
```

### Manual SSL

```bash
# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx.key \
    -out /etc/nginx/ssl/nginx.crt

# Update nginx config
sudo nano /etc/nginx/sites-available/missioncontrol
```

**Add to server block**:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring

### Health Checks

**Backend health endpoint**:

```bash
# Check health
curl https://your-domain.com/health

# Expected response
{"status": "healthy"}
```

**Frontend health**:

```bash
curl https://your-domain.com/
```

### Logs

**Docker logs**:

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail 100 backend
```

**Systemd logs**:

```bash
# View service logs
sudo journalctl -u missioncontrol-backend -f

# View last 100 lines
sudo journalctl -u missioncontrol-backend --lines 100
```

### Metrics (Optional)

**Prometheus + Grafana setup**:

```yaml
# docker-compose.yml additions
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
```

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -h localhost -U mcuser -d mission_control

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

### Backend Not Starting

```bash
# Check logs
sudo journalctl -u missioncontrol-backend -n 50

# Test manually
cd /opt/openclaw-mission-control/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### Frontend Build Errors

```bash
# Clear cache
rm -rf node_modules .next
npm ci
npm run build
```

### Nginx Errors

```bash
# Test config
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Check access logs
sudo tail -f /var/log/nginx/access.log
```

### Rate Limiting

If you hit OpenClaw rate limits:

1. Check OpenClaw Gateway status
2. Adjust heartbeat frequencies (increase intervals)
3. Implement exponential backoff in your code
4. Consider upgrading OpenClaw plan

## Security Checklist

- [ ] Change default passwords
- [ ] Use strong PostgreSQL password
- [ ] Enable SSL/TLS
- [ ] Configure firewall (ufw/iptables)
- [ ] Keep secrets in environment variables
- [ ] Disable DEBUG mode
- [ ] Enable CORS only for specific origins
- [ ] Set up fail2ban
- [ ] Regular security updates
- [ ] Database backups

## Backup Strategy

### Database Backups

```bash
# Create backup
pg_dump mission_control > backup_$(date +%Y%m%d).sql

# Restore backup
psql mission_control < backup_YYYYMMDD.sql

# Automated backup (cron)
# Edit crontab: crontab -e
# Add: 0 2 * * * pg_dump mission_control > /backups/mc_$(date +\%Y\%m\%d).sql
```

### Docker Volumes

```bash
# Backup volume
docker run --rm -v mission_control_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore volume
docker run --rm -v mission_control_postgres_data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/postgres_backup.tar.gz"
```

## Performance Tuning

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX idx_agent_logs_agent_id ON agent_logs(agent_id);
CREATE INDEX idx_agent_logs_created_at ON agent_logs(created_at);
```

### Connection Pooling (PgBouncer)

```yaml
# Add to docker-compose.yml
  pgbouncer:
    image: pgbouncer/pgbouncer
    environment:
      DATABASES_HOST: postgres
      DATABASES_PORT: 5432
      DATABASES_DATABASE: mission_control
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 25
    ports:
      - "6432:6432"
```

## Updates

### Rolling Updates (Docker)

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Check status
docker-compose ps
```

### Zero-Downtime Updates (Blue/Green)

```bash
# Build new version
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start new version on different port
docker-compose -f docker-compose.yml -f docker-compose.prod.yml -p mc_green up -d

# Switch traffic
docker-compose -f docker-compose.blue.yml down
```

---

For questions or issues, please check the [Troubleshooting Guide](TROUBLESHOOTING.md) or open an issue on GitHub.
