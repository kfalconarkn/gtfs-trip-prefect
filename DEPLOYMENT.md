# GTFS ETL Prefect v3 Deployment Guide

This guide explains how to deploy the GTFS ETL flow to Prefect Cloud using Prefect v3.

## Prerequisites

1. Prefect v3 installed (`pip install prefect>=3.0.0`)
2. Authenticated to Prefect Cloud (`prefect cloud login`)
3. Python 3.9+ and all dependencies from `requirements.txt`

## Deployment Steps

### 1. Using the Existing Work Pool

This deployment will use the existing "Main" work pool that is already set up in your Prefect Cloud workspace. No additional work pool creation is needed.

### 2. Deploy the Flow

Deploy the flow to the existing "Main" work pool:

```bash
python deploy.py
```

This script:
- Uses the `flow.deploy()` method to create a deployment
- Deploys the `fetch_gtfs_stops_flow` to Prefect Cloud
- Sets up a scheduled run every 360 seconds (6 minutes)
- Configures the deployment to use the existing "Main" work pool
- Uses a process-based DeploymentImage to run the flow from local code
- Includes the `requirements.txt` file to install dependencies at runtime

### 3. Verify Deployment

After deploying, verify that your deployment appears in the Prefect Cloud UI:
1. Go to your Prefect Cloud workspace
2. Navigate to "Deployments" tab
3. Look for "gtfs-stops-flow" deployment

## Configuration Details

### Work Pool Configuration

The deployment uses the existing "Main" work pool in your Prefect Cloud workspace.

### Deployment Image

The deployment uses a process-based DeploymentImage, which means:
- The flow code will be executed directly from your local environment
- No Docker container is required
- The code doesn't need to be pushed to a remote storage location

### Deployment Configuration

The deployment is configured with:
- **Name**: gtfs-stops-flow
- **Schedule**: Runs every 360 seconds (6 minutes)
- **Work Pool**: Main (existing work pool)
- **Dependencies**: Uses requirements.txt for runtime dependency installation
- **Tags**: gtfs, etl, main-kinetic, default

### Environment Variables

The deployment sets these environment variables:
- `PREFECT_LOGGING_LEVEL`: INFO

## Running the Flow Manually

You can trigger a flow run manually from the Prefect Cloud UI:
1. Go to your deployment in Prefect Cloud
2. Click "Create Flow Run"
3. (Optional) Adjust any parameters
4. Click "Run"

## Monitoring

Monitor flow runs in the Prefect Cloud UI:
1. Go to your Prefect Cloud workspace
2. Navigate to "Flow Runs" tab
3. View run history, logs, and metrics

## Troubleshooting

If you encounter issues with your deployment:

1. Check the deployment logs in Prefect Cloud
2. Ensure all dependencies are correctly specified in `requirements.txt`
3. Verify that Prefect Cloud authentication is current
4. Confirm that the work pool is properly configured and active 