#!/bin/bash

# Set environment variables
# NOTE: You need to replace this with a valid Logfire token
# The current token is causing 401 errors
export LOGFIRE_TOKEN="pylf_v1_us_r8nwb7ycg8bSxsSnjktwMJ1cV3s0sLlwTvCNvdNTpm8ngrep"

# Redis connection details
export REDIS_HOST="redis-11529.c323.us-east-1-2.ec2.redns.redis-cloud.com"
export REDIS_PORT="11529"
export REDIS_PASSWORD="wgk1Spj42pld4hm7xKbXHyhqfyd1NhEU"

# Print environment variables for debugging
echo "Environment variables:"
echo "LOGFIRE_TOKEN: ${LOGFIRE_TOKEN:0:5}...${LOGFIRE_TOKEN: -5}"
echo "REDIS_HOST: $REDIS_HOST"
echo "REDIS_PORT: $REDIS_PORT"
echo "REDIS_PASSWORD: ${REDIS_PASSWORD:0:5}...${REDIS_PASSWORD: -5}"

# Activate virtual environment
source env/bin/activate

# Run the Python script with output logging
nohup python gtfs_stops.py > gtfs_etl.log 2>&1 &

# Get the process ID
PID=$!
echo "Started gtfs_stops.py with PID: $PID"
echo "Check gtfs_etl.log for output"


