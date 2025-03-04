from functions import fetch_and_process_trip_updates
from prefect import flow, task
import redis
import json
from datetime import timedelta
import asyncio
import time


@task(name="Fetch GTFS stop updates", log_prints=True)
async def fetch_gtfs_stops_task():
    # Add async keyword and use await since fetch_and_process_trip_updates is an async function
    response = await fetch_and_process_trip_updates()
    return response

@task(name="Upload GTFS stops to redis", log_prints=True, cache_policy=None, retries=3, retry_delay_seconds=5)  # Add retry capabilities
def upload_gtfs_stops_to_redis_task(response):
    """ Upload data to redis
    
    This task implements the upload rules specified in the PRD:
    1. Each trip_id/route_id combo is unique, and child stops data should be appended/updated
    2. If stop_id/stop_sequence doesn't exist, append it
    3. If stop_id/stop_sequence exists, update the departure_delay
    4. Set data expiry to 36 hours
    """
    print("Connecting to Redis...")
    start_time = time.time()
    
    # Connection pool settings
    pool = redis.ConnectionPool(
        host='redis-11529.c323.us-east-1-2.ec2.redns.redis-cloud.com',
        port=11529,
        decode_responses=True,
        username="default",
        password="wgk1Spj42pld4hm7xKbXHyhqfyd1NhEU",
        max_connections=10,  # Adjust based on expected concurrency
        health_check_interval=30  # Check connection health every 30 seconds
    )
    
    try:
        r = redis.Redis(connection_pool=pool)
        
        # Test the connection
        ping_response = r.ping()
        if ping_response:
            print(f"Successfully connected to Redis at {r.connection_pool.connection_kwargs['host']}:{r.connection_pool.connection_kwargs['port']}")
            print(f"Redis server info: {r.info('server')['redis_version']}")
            print(f"Current database size: {r.dbsize()} keys")
        else:
            print("Warning: Redis connection established but ping test failed")
    except redis.ConnectionError as e:
        print(f"Error connecting to Redis: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during Redis connection: {type(e).__name__}: {e}")
        raise
    
    # Set expiry time (36 hours in seconds)
    expiry_seconds = int(timedelta(hours=36).total_seconds())
    
    # Create lists to store keys, values, and expiry operations for batch processing
    print(f"Processing {len(response)} trips for batch upload...")
    
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
        print(f"Found {existing_keys_count} existing keys that need to be updated")
        
        for key, exists in key_exists.items():
            if exists:
                pipe.get(key)
        
        # Execute the pipeline to get all existing data
        existing_data_results = pipe.execute()
        
        # Performance optimization - pre-allocate the pipeline size
        # based on expected operations (2 ops per trip - set and expire)
        pipeline_size = len(response) * 2
        updates_pipe = r.pipeline(transaction=False)
        
        existing_data_index = 0
        update_count = 0
        create_count = 0
        
        # Process all trips and prepare batch operations
        for i, trip in enumerate(response):
            # Periodically execute the pipeline to avoid large memory usage
            # Flush every 1000 operations (500 trips)
            if i > 0 and i % 500 == 0 and updates_pipe:
                print(f"Executing intermediate batch at trip {i}...")
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
            print(f"Executing final batch operations: {update_count} updates and {create_count} new entries...")
            updates_pipe.execute()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        ops_per_second = len(response) / elapsed_time if elapsed_time > 0 else 0
        
        print(f"Successfully processed {len(response)} trips to Redis using batch operations")
        print(f"  - Updated {update_count} existing entries")
        print(f"  - Created {create_count} new entries")
        print(f"  - All keys set to expire in {expiry_seconds} seconds (36 hours)")
        print(f"  - Total time: {elapsed_time:.2f} seconds ({ops_per_second:.2f} operations/second)")
        
    except redis.RedisError as e:
        print(f"Redis error during batch operation: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error during batch operation: {type(e).__name__}: {e}")
        raise
    finally:
        # Clean up the connection pool if needed
        pass


@flow(name="Fetch GTFS Stops Flow", log_prints=True)
async def fetch_gtfs_stops_flow():
    # Make the flow async too
    response = await fetch_gtfs_stops_task()
    upload_gtfs_stops_to_redis_task(response)


if __name__ == "__main__":
    # Run the async flow with asyncio
    asyncio.run(fetch_gtfs_stops_flow())