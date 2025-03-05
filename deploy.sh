#!/bin/bash

# Set environment variables

# Redis connection details
export REDIS_HOST="redis-11529.c323.us-east-1-2.ec2.redns.redis-cloud.com"
export REDIS_PORT="11529"
export REDIS_PASSWORD="wgk1Spj42pld4hm7xKbXHyhqfyd1NhEU"

# Print environment variables for debugging
echo "Environment variables:"
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


