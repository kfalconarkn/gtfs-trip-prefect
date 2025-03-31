from functions import fetch_and_process_trip_updates
import redis
import json
from datetime import timedelta, datetime
import asyncio
import time
import logfire
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This will not override existing environment variables, so GitHub Actions env vars will take precedence
load_dotenv()

# Get environment variables with no default values
# This ensures we don't expose sensitive information in the code
LOGFIRE_TOKEN = os.environ.get('LOGFIRE_TOKEN')
REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
REDIS_EXPIRY_HOURS = int(os.environ.get('REDIS_EXPIRY_HOURS', '12'))  # Default expiry as fallback

# Configure logfire
if LOGFIRE_TOKEN:
    logfire.configure(token=LOGFIRE_TOKEN)
else:
    logfire.info("LOGFIRE_TOKEN not set, logging may be limited")

# Validate required environment variables
required_vars = ['REDIS_HOST', 'REDIS_PASSWORD']
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    logfire.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)


async def fetch_gtfs_stops_task():
    # Add async keyword and use await since fetch_and_process_trip_updates is an async function
    response = await fetch_and_process_trip_updates()
    return response


def upload_gtfs_stops_to_redis_task(response):
    """ Upload data to Redis
    
    This task implements the upload rules specified in the PRD:
    1. Each trip_id/route_id combo is unique, and child stops data should be appended/updated
    2. If stop_id/stop_sequence doesn't exist, append it
    3. If stop_id/stop_sequence exists, update the departure_delay
    4. Set data expiry to 12 hours (configurable via environment variable)
    """
    logfire.info("Connecting to Redis...")
    start_time = time.time()
    
    try:
        # Create Redis client
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            decode_responses=True,
            socket_timeout=10.0,
            socket_connect_timeout=10.0,
            health_check_interval=30,
            retry_on_timeout=True,
            # Limited to 5 max connections to accommodate free tier Redis service
            max_connections=5
        )
        
        # Test the connection
        ping_response = r.ping()
        if ping_response:
            logfire.info(f"Successfully connected to Redis at {REDIS_HOST}")
            logfire.info(f"Current database size: {r.dbsize()} keys")
        else:
            logfire.warning("Warning: Redis connection established but ping test failed")
    except redis.ConnectionError as e:
        logfire.error(f"Error connecting to Redis: {e}")
        raise
    except Exception as e:
        logfire.error(f"Unexpected error during Redis connection: {type(e).__name__}: {e}")
        raise
    
    # Set expiry time (12 hours in seconds by default, configurable via environment variable)
    expiry_seconds = int(timedelta(hours=REDIS_EXPIRY_HOURS).total_seconds())
    
    # Create lists to store keys, values, and expiry operations for batch processing
    logfire.info(f"Processing {len(response)} trips for batch upload...")
    
    # First, fetch all existing keys in one batch operation
    trip_keys = [f"gtfs:{trip['trip_id']}:{trip['route_id']}" for trip in response]
    
    try:
        # Create pipeline for bulk fetching existing keys
        pipe = r.pipeline(transaction=False)
        for key in trip_keys:
            pipe.exists(key)
        
        # Execute the pipeline and get results
        exist_results = pipe.execute()
        
        # Create a dictionary mapping keys to their exist status
        key_exists = {key: exists for key, exists in zip(trip_keys, exist_results)}
        
        # Fetch all existing data that needs updating in bulk
        pipe = r.pipeline(transaction=False)
        
        # Count how many existing keys we need to fetch
        existing_keys_count = sum(1 for exists in key_exists.values() if exists)
        logfire.info(f"Found {existing_keys_count} existing keys that need to be updated")
        
        for key, exists in key_exists.items():
            if exists:
                pipe.get(key)
        
        # Execute the pipeline to get all existing data
        existing_data_results = pipe.execute()
        
        # Performance optimization - pre-allocate the pipeline size for batch processing
        # Since we're not in a serverless environment, we can use larger batches
        updates_pipe = r.pipeline(transaction=False)
        
        existing_data_index = 0
        update_count = 0
        create_count = 0
        
        # Process all trips and prepare batch operations
        for i, trip in enumerate(response):
            # Periodically execute the pipeline to avoid large memory usage
            # Flush every 1000 operations (500 trips)
            if i > 0 and i % 1000 == 0 and updates_pipe:
                logfire.info(f"Executing intermediate batch at trip {i}...")
                updates_pipe.execute()
                updates_pipe = r.pipeline(transaction=False)
            
            trip_id = trip['trip_id']
            route_id = trip['route_id']
            key = f"gtfs:{trip_id}:{route_id}"
            
            if key_exists[key]:
                # Update existing entry
                existing_data = json.loads(existing_data_results[existing_data_index])
                existing_data_index += 1
                
                existing_stops = {f"{stop['stop_id']}:{stop['stop_sequence']}": stop for stop in existing_data['stops']}
                
                # Update existing stops and add new ones
                for stop in trip['stops']:
                    stop_key = f"{stop['stop_id']}:{stop['stop_sequence']}"
                    
                    if stop_key in existing_stops:
                        # Update departure_delay for existing stop
                        existing_stops[stop_key]['departure_delay'] = stop['departure_delay']
                        existing_stops[stop_key]['departure_time'] = stop['departure_time']
                    else:
                        # Add new stop
                        existing_stops[stop_key] = stop
                
                # Convert back to list format
                updated_data = {
                    'trip_id': trip_id,
                    'route_id': route_id,
                    'stops': list(existing_stops.values())
                }
                
                # Add to pipeline - set updated data and expiry
                updates_pipe.set(key, json.dumps(updated_data))
                updates_pipe.expire(key, expiry_seconds)
                update_count += 1
                
            else:
                # Create new entry
                updates_pipe.set(key, json.dumps(trip))
                updates_pipe.expire(key, expiry_seconds)
                create_count += 1
        
        # Execute all remaining updates in a single batch
        if updates_pipe:
            logfire.info(f"Executing final batch operations: {update_count} updates and {create_count} new entries...")
            updates_pipe.execute()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        ops_per_second = len(response) / elapsed_time if elapsed_time > 0 else 0
        
        # Log results
        logfire.info(f"✅ Successfully processed {len(response)} trips to Redis using batch operations")
        logfire.info(f"✅ Updated {update_count} existing entries")
        logfire.info(f"✅ Created {create_count} new entries")
        logfire.info(f"All keys set to expire in {expiry_seconds} seconds ({REDIS_EXPIRY_HOURS} hours)")
        logfire.info(f"Total time: {elapsed_time:.2f} seconds ({ops_per_second:.2f} operations/second)")
        
    except redis.RedisError as e:
        logfire.error(f"Redis error during batch operation: {e}")
        raise
    except Exception as e:
        logfire.error(f"Unexpected error during batch operation: {type(e).__name__}: {e}")
        raise
    finally:
        # No need to close the connection pool since Redis will handle it
        logfire.info("Redis operations completed")


async def fetch_gtfs_stops_flow():
    """Main ETL flow that fetches GTFS data and uploads it to Redis"""
    logfire.info("Starting GTFS etl process")
    try:
        response = await fetch_gtfs_stops_task()
        upload_gtfs_stops_to_redis_task(response)
        logfire.info("GTFS stops flow completed successfully")
        return True
    except Exception as e:
        logfire.error(f"Error in GTFS stops flow: {type(e).__name__}: {e}")
        return False


async def main():
    """Main function to run the ETL process once"""
    start_time = time.time()
    
    try:
        success = await fetch_gtfs_stops_flow()
        if success:
            logfire.info("ETL process completed successfully")
            elapsed_time = time.time() - start_time
            logfire.info(f"Total execution time: {elapsed_time:.2f} seconds")
            return 0
        else:
            logfire.error("ETL process failed")
            return 1
    except Exception as e:
        logfire.error(f"Unhandled error in ETL process: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    # Run the ETL process once and exit
    exit_code = asyncio.run(main())
    sys.exit(exit_code)