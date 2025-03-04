# GTFS feed ETL project

## Overview
This ETL project aims to take bus trip update information from a realtime GTFS API, 
transform the data to a parent child structure. The processed data will then be uploaded 
to redis cloud using prefect cloud deployment. 

## Tech stack
- Python
- Prefect 
- Redis

## prefect details

Owning Account
main-kinetic
Handle
default
Description
None
Workspace ID
54a82305-16da-45e4-b181-0948b49ce93a


## API 
GTFS data contains stop level information for each trip_id. Each trip_id should be filtered to filter and return only the min() stop sequence and the next stop sequence for each trip_id.

this is an example of the required output structure:
{
        "trip_id": "31999893-SBL 24_25-38705",
        "route_id": "700-4067",
        "stops": [
            {
                "stop_id": "300333",
                "departure_delay": 147,
                "departure_time": "2025-03-01 10:05:27",
                "stop_sequence": 1
            },
            {
                "stop_id": "300335",
                "departure_delay": 121,
                "departure_time": "2025-03-01 10:07:01",
                "stop_sequence": 2

            }
        ]
    },

## Redis 
JSON structure is uploaded to redis.
Upload rules:

1. Each combo of trip_id and route_id is unique and child stops data should be appeneded and or updated to that trip_id/route_id. when the gtfs api data is fetched and the combo of stop_id, stop dequence is not present in the redis db, then it should be appeneded to that trip_id. If the stop_id/stop equence exists then the departure_delay data for that stop_id should be updated. 
2. The data expirary that is uploaded should be 36 hours. 

Connection exmaple:

"""Basic connection example.
"""

import redis

r = redis.Redis(
    host='redis-11529.c323.us-east-1-2.ec2.redns.redis-cloud.com',
    port=11529,
    decode_responses=True,
    username="default",
    password="wgk1Spj42pld4hm7xKbXHyhqfyd1NhEU",
)


## Data Flow

1. Data is downloaded from GTFS API
2. Data is transformed to required format
3. Data is uploaded/appened to redis db.
