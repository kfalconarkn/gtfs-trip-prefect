# GTFS Prefect ETL

This project fetches GTFS (General Transit Feed Specification) real-time data and processes it using Prefect workflows, then stores the data in Redis.

## Overview

The ETL pipeline:
1. Fetches GTFS real-time data
2. Transforms it into a parent-child structure
3. Uploads the processed data to Redis Cloud
4. Sets up automatic scheduling via Prefect Cloud

## Dependencies

Dependencies are managed in the `requirements.txt` file and will be automatically installed at runtime when using Prefect Managed infrastructure.

## Important Note on Async Functions

This flow uses asynchronous functions. Make sure your `functions.py` implements `fetch_and_process_trip_updates()` as an async function:

```python
# Example implementation in functions.py
async def fetch_and_process_trip_updates():
    # Your async implementation here
    # ...
    return processed_data
```

## Workspace Details

This project is configured to run on the following Prefect Cloud workspace:
- Account: main-kinetic
- Workspace ID: 54a82305-16da-45e4-b181-0948b49ce93a

## Deployment Options

### Option 1: Easy Setup (Recommended)

Run the setup script that creates a managed work pool and deploys the flow:

```bash
# First, login to Prefect Cloud
prefect cloud login -k YOUR_API_KEY

# Then run the setup script
python setup_and_deploy.py
```

### Option 2: Using flow.serve() (Direct Method)

```bash
python gtfs_stops.py
```

This will run the flow locally with runtime dependencies.

### Option 3: Manual Deployment with prefect.yaml

```bash
# Create a managed work pool
prefect work-pool create prefect-managed-pool --type prefect:managed

# Deploy using prefect.yaml
prefect deploy
```

## Running Your Flow

After deployment, you can run your flow through:

1. **Prefect UI**: Go to your workspace and trigger the deployment
2. **Prefect CLI**:
```bash
prefect deployment run 'Fetch GTFS Stops Flow/GTFS Stops Deployment'
```

## Monitoring

Your flow will run on the specified schedule (every 360 seconds) and will automatically install dependencies from requirements.txt at runtime on Prefect's managed infrastructure.

## Troubleshooting

If you encounter issues:

1. Verify you're authenticated to the correct workspace:
```bash
prefect cloud workspace set --workspace "kinetic/default"
```

2. Ensure your requirements.txt file is correct and in the project root

3. Check the Prefect Cloud logs for any runtime errors

4. Redis Connection Issues:
   - Verify your Redis credentials in the redis connection string
   - Make sure your network allows connections to the Redis server
   - The username-password pair must be valid for the Redis instance
