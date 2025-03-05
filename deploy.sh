#!/bin/bash

# Set environment variables
export LOGFIRE_TOKEN="pylf_v1_us_r8nwb7ycg8bSxsSnjktwMJ1cV3s0sLlwTvCNvdNTpm8ngrep"
export REDIS_HOST="redis-11529.c323.us-east-1-2.ec2.redns.redis-cloud.com"
export REDIS_PORT="11529"
export REDIS_PASSWORD="wgk1Spj42pld4hm7xKbXHyhqfyd1NhEU"

# Activate virtual environment
source env/bin/activate

# Run the Python script
nohup python gtfs_stops.py &

# print out success message
echo "Successfully deployed gtfs_stops.py"


