# Docker Deployment Guide

This guide explains how to deploy the GTFS ETL application using Docker and Dokploy.

## Overview

The application has been containerized to run continuously, executing the ETL process at regular intervals (default: every 60 seconds). This allows for seamless deployment on Dokploy or any Docker-compatible hosting platform.

## Files Added

- `Dockerfile` - Container image definition
- `docker-compose.yml` - Docker Compose configuration for easy deployment
- `run_continuous.py` - Wrapper script that runs the ETL process continuously
- `.dockerignore` - Files to exclude from the Docker image
- `.env.example` - Example environment variables file

## Environment Variables

The following environment variables are required for deployment:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LOGFIRE_TOKEN` | LogFire API token for logging | Yes | - |
| `REDIS_HOST` | Redis server hostname | Yes | - |
| `REDIS_PORT` | Redis server port | No | 11529 |
| `REDIS_USERNAME` | Redis username | Yes | - |
| `REDIS_PASSWORD` | Redis password | Yes | - |
| `REDIS_EXPIRY_HOURS` | Data expiry time in hours | No | 18 |
| `RUN_INTERVAL_SECONDS` | How often to run ETL (in seconds) | No | 60 |

## Local Testing with Docker

### 1. Build the Docker image

```bash
cd gtfs-trip-prefect
docker build -t gtfs-trip-etl .
```

### 2. Create a .env file

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 3. Run with Docker Compose

```bash
docker-compose up -d
```

### 4. View logs

```bash
docker-compose logs -f
```

### 5. Stop the container

```bash
docker-compose down
```

## Deployment on Dokploy

Dokploy supports multiple deployment methods. Here are the recommended approaches:

### Method 1: Docker Compose (Recommended)

1. **Create a new service in Dokploy**
   - Navigate to your Dokploy dashboard
   - Click "Create New Service"
   - Select "Docker Compose"

2. **Upload your docker-compose.yml**
   - Copy the contents of `docker-compose.yml`
   - Paste it into the Dokploy configuration

3. **Set environment variables**
   - In Dokploy, navigate to your service's environment variables section
   - Add all required environment variables (listed above)
   - Dokploy will automatically inject these into your container

4. **Deploy**
   - Click "Deploy" or "Start"
   - Monitor the logs to ensure successful startup

### Method 2: Git Repository Deployment

1. **Push your code to a Git repository** (GitHub, GitLab, etc.)

2. **Create a new service in Dokploy**
   - Select "Git Repository"
   - Connect your repository

3. **Configure build settings**
   - Dokploy will automatically detect the Dockerfile
   - Set the build context to the repository root

4. **Set environment variables**
   - Add all required environment variables in Dokploy's interface

5. **Deploy**
   - Dokploy will automatically build and deploy your container

### Method 3: Docker Image

1. **Build and push to a registry**

```bash
# Build the image
docker build -t your-registry/gtfs-trip-etl:latest .

# Push to registry (Docker Hub, GitHub Container Registry, etc.)
docker push your-registry/gtfs-trip-etl:latest
```

2. **Create service in Dokploy**
   - Select "Docker Image"
   - Enter your image name: `your-registry/gtfs-trip-etl:latest`

3. **Set environment variables and deploy**

## Configuration Options

### Adjusting Run Interval

To change how often the ETL process runs, set the `RUN_INTERVAL_SECONDS` environment variable:

- `60` - Runs every minute (default)
- `300` - Runs every 5 minutes
- `3600` - Runs every hour

### Resource Limits

The `docker-compose.yml` includes default resource limits:
- CPU: 0.5 cores max, 0.25 cores reserved
- Memory: 512MB max, 256MB reserved

Adjust these in the `docker-compose.yml` file based on your needs:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## Monitoring

### Health Checks

The container includes a basic health check that runs every 60 seconds. You can monitor the health status with:

```bash
docker ps
```

### Logs

All logs are sent to LogFire (if configured) and to Docker logs. View Docker logs with:

```bash
# Docker Compose
docker-compose logs -f

# Docker
docker logs -f gtfs-trip-etl

# In Dokploy
# Use the built-in logs viewer in the dashboard
```

### Log Rotation

Logs are automatically rotated with the following settings:
- Max size: 10MB per file
- Max files: 3

## Troubleshooting

### Container keeps restarting

1. Check the logs for error messages
2. Verify all environment variables are set correctly
3. Ensure Redis is accessible from the container
4. Check that LOGFIRE_TOKEN is valid

### ETL process not running at expected interval

1. Check the `RUN_INTERVAL_SECONDS` environment variable
2. Monitor logs to see actual run times
3. If ETL takes longer than the interval, it will run immediately after completion

### Connection issues to Redis

1. Verify Redis host and port are correct
2. Check that Redis is accessible from your Dokploy environment
3. Verify Redis credentials
4. Ensure firewall/security groups allow the connection

### Out of memory errors

1. Increase memory limits in `docker-compose.yml`
2. Monitor actual memory usage with `docker stats`
3. Consider reducing `RUN_INTERVAL_SECONDS` if processing too frequently

## Security Best Practices

1. **Never commit .env files** - They contain sensitive credentials
2. **Use secrets management** - Use Dokploy's built-in secrets/environment variables feature
3. **Regularly rotate credentials** - Update Redis passwords and LogFire tokens periodically
4. **Monitor access logs** - Check Redis and LogFire for unauthorized access
5. **Use private registries** - If pushing Docker images, use private container registries

## Updating the Application

### On Dokploy (Git deployment)

1. Push changes to your Git repository
2. In Dokploy, click "Redeploy" or enable auto-deployment
3. Monitor the build and deployment logs

### On Dokploy (Docker Compose)

1. Update your code locally
2. Build and test locally
3. Update the `docker-compose.yml` in Dokploy if needed
4. Click "Redeploy"

### Manual update

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

## Support

If you encounter issues:

1. Check the application logs in Dokploy or Docker
2. Verify all environment variables are set correctly
3. Review the LogFire dashboard for detailed error information
4. Ensure Redis is operational and accessible
