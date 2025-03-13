# GTFS feed ETL project

## Overview
This ETL project aims to take bus trip update information from a realtime GTFS API, 
transform the data to a parent child structure. The processed data will then be uploaded 
to redis cloud using prefect cloud deployment. 

## Tech stack
- Python
- Redis



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

## Upstash (Redis)
Data (json structure) is to be uploaded to upstach redis db.

Upload rules:
1. Each combo of trip_id and route_id is unique and child stops data should be appeneded and or updated to that trip_id/route_id. when the gtfs api data is fetched and the combo of stop_id, stop dequence is not present in the redis db, then it should be appeneded to that trip_id. If the stop_id/stop equence exists then the departure_delay data for that stop_id should be updated. 
2. The data expirary that is uploaded should be 12 hours. 

Connection creditials:
Enpoint: concise-sculpin-61825.upstash.io
port: 6379


## Logging

Pydantic lofire will be used to send logging information to the platform for observibility and monitoring. 

## Data Flow

1. Data is downloaded from GTFS API
2. Data is transformed to required format
3. Data is uploaded/appened to redis db.

## Deployment
Python script will be deployed to github actions. yml file will specify the deployment config
the github action s will run every 1 min via a google schedule http call. dependencies will be defined using the requirements.txt file in the root dir. 