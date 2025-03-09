# GTFS Feed ETL Project

## Overview
This ETL project fetches bus trip update information from a realtime GTFS API, transforms the data to a parent-child structure, and uploads the processed data to Redis Cloud. The ETL process is deployed using GitHub Actions, which runs the script at regular intervals.

## Features
- Fetches real-time GTFS trip updates from the Translink API
- Filters and processes the data to include only the minimum stop sequence and the next one for each trip
- Uploads the processed data to Redis Cloud with proper data management:
  - Each trip_id/route_id combination is unique
  - Child stops data is appended or updated as needed
  - Data expires after 12 hours (configurable)
- Deployed using GitHub Actions to run every minute
- Comprehensive logging with LogFire
- Environment variable configuration via .env file for local development

## Tech Stack
- Python 3.10+
- Redis
- GitHub Actions
- LogFire for logging
- python-dotenv for environment variable management

## Project Structure
- `gtfs_stops.py` - Main ETL script
- `functions.py` - Helper functions for fetching and processing GTFS data
- `.github/workflows/gtfs_etl.yml` - GitHub Actions workflow configuration
- `requirements.txt` - Python dependencies
- `.env` - Environment variables for local development (not committed to the repository)

## Setup and Configuration

### Local Development
1. Clone the repository
2. Create a `.env` file in the root directory with the following variables:
   ```
   REDIS_HOST=your_redis_host
   REDIS_PORT=your_redis_port
   REDIS_USERNAME=your_redis_username
   REDIS_PASSWORD=your_redis_password
   REDIS_EXPIRY_HOURS=12
   LOGFIRE_TOKEN=your_logfire_token
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the script:
   ```
   python gtfs_stops.py
   ```

### Environment Variables
The following environment variables are required:

| Variable | Description | Required |
|----------|-------------|----------|
| `LOGFIRE_TOKEN` | LogFire API token | Yes |
| `REDIS_HOST` | Redis host | Yes |
| `REDIS_PORT` | Redis port | Yes (defaults to 11529) |
| `REDIS_USERNAME` | Redis username | Yes |
| `REDIS_PASSWORD` | Redis password | Yes |
| `REDIS_EXPIRY_HOURS` | Hours until data expires | Yes (defaults to 12) |

### GitHub Actions Setup
1. Go to your GitHub repository settings
2. Navigate to Secrets and Variables > Actions
3. Add the following repository secrets:
   - `LOGFIRE_TOKEN`
   - `REDIS_HOST`
   - `REDIS_PORT`
   - `REDIS_USERNAME`
   - `REDIS_PASSWORD`

### Security Note
- The `.env` file contains sensitive information and should **never** be committed to the repository
- Add `.env` to your `.gitignore` file to prevent accidental commits
- For production, always use GitHub Secrets to store sensitive information

## Data Structure
The ETL process transforms the GTFS data into the following structure:

```json
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
}
```

## Redis Data Management
- Each trip_id/route_id combination is stored as a unique key in Redis
- The key format is `gtfs:{trip_id}:{route_id}`
- If a stop_id/stop_sequence doesn't exist in Redis, it's appended to the trip
- If a stop_id/stop_sequence exists, its departure_delay and departure_time are updated
- All data expires after 12 hours (configurable via environment variables)

## Logging
The application uses LogFire for comprehensive logging. Key events that are logged include:
- ETL process start and completion
- Redis connection status
- Data processing statistics
- Errors and exceptions

## Troubleshooting
If the ETL process fails, check the following:
1. Verify that all environment variables are correctly set in your `.env` file (local) or GitHub Secrets (GitHub Actions)
2. Ensure Redis connection details are correct
3. Check GitHub Actions logs for detailed error messages
4. Verify that the GTFS API is accessible and returning valid data 