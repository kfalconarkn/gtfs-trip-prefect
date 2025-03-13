from functions import fetch_and_process_trip_updates
import pymongo
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
MONGO_USERNAME = os.environ.get('MONGO_USERNAME')
MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD')
MONGO_URI = os.environ.get('MONGO_URI', f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@cluster0.dsh19.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'gtfs_data')
MONGO_COLLECTION = os.environ.get('MONGO_COLLECTION', 'trips_stops')
REDIS_EXPIRY_HOURS = int(os.environ.get('REDIS_EXPIRY_HOURS', '12'))  # Keeping this for TTL index in MongoDB

# Configure logfire
if LOGFIRE_TOKEN:
    logfire.configure(token=LOGFIRE_TOKEN)
else:
    logfire.info("LOGFIRE_TOKEN not set, logging may be limited")

# Validate required environment variables
required_vars = ['MONGO_USERNAME', 'MONGO_PASSWORD']
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    logfire.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)


async def fetch_gtfs_stops_task():
    # Add async keyword and use await since fetch_and_process_trip_updates is an async function
    response = await fetch_and_process_trip_updates()
    return response


def upload_gtfs_stops_to_mongodb_task(response):
    """ Upload data to MongoDB
    
    This task implements the upload rules specified in the PRD:
    1. Each trip_id/route_id combo is unique, and child stops data should be appended/updated
    2. If stop_id/stop_sequence doesn't exist, append it
    3. If stop_id/stop_sequence exists, update the departure_delay
    4. Set data expiry to 12 hours (configurable via environment variable)
    """
    logfire.info("Connecting to MongoDB...")
    start_time = time.time()
    
    try:
        # Create MongoDB client
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION]
        
        # Test the connection
        server_info = client.server_info()
        logfire.info(f"Successfully connected to MongoDB")
        logfire.info(f"Current collection size: {collection.count_documents({})} documents")
        
        # Ensure TTL index exists for automatic expiry
        # This will create an index on created_at field that will expire documents after REDIS_EXPIRY_HOURS
        expiry_seconds = int(timedelta(hours=REDIS_EXPIRY_HOURS).total_seconds())
        collection.create_index("created_at", expireAfterSeconds=expiry_seconds)
        
        logfire.info(f"Processing {len(response)} trips for batch upload...")
        
        # Performance metrics
        update_count = 0
        create_count = 0
        
        # Using bulk operations for better performance
        bulk_operations = []
        
        # Current time for TTL index - use timezone-aware datetime object
        try:
            # For Python 3.11+ which has datetime.UTC
            current_time = datetime.now(datetime.UTC)
        except AttributeError:
            # Fallback for older Python versions
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
        
        # Process all trips and prepare bulk operations
        for trip in response:
            trip_id = trip['trip_id']
            route_id = trip['route_id']
            
            # Create a composite key for trip_id and route_id
            filter_query = {
                "trip_id": trip_id,
                "route_id": route_id
            }
            
            # Check if the document exists
            existing_doc = collection.find_one(filter_query)
            
            if existing_doc:
                # Update existing entry
                update_operations = []
                
                # Convert existing stops to a dictionary for easier lookup
                existing_stops = {f"{stop['stop_id']}:{stop['stop_sequence']}": stop 
                                 for stop in existing_doc.get('stops', [])}
                
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
                updated_stops = list(existing_stops.values())
                
                # Create update operation
                update_operation = pymongo.UpdateOne(
                    filter_query,
                    {
                        "$set": {
                            "stops": updated_stops,
                            "created_at": current_time,  # Update the TTL field
                        }
                    }
                )
                
                bulk_operations.append(update_operation)
                update_count += 1
                
            else:
                # Create new entry
                trip["created_at"] = current_time  # Add TTL field
                
                # Create insert operation
                insert_operation = pymongo.InsertOne(trip)
                
                bulk_operations.append(insert_operation)
                create_count += 1
            
            # Execute bulk operations in chunks to avoid large memory usage
            if len(bulk_operations) >= 500:
                logfire.info(f"Executing intermediate batch of {len(bulk_operations)} operations...")
                result = collection.bulk_write(bulk_operations, ordered=False)
                bulk_operations = []
        
        # Execute any remaining bulk operations
        if bulk_operations:
            logfire.info(f"Executing final batch of {len(bulk_operations)} operations...")
            result = collection.bulk_write(bulk_operations, ordered=False)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        ops_per_second = len(response) / elapsed_time if elapsed_time > 0 else 0
        
        # Log results
        logfire.info(f"✅ Successfully processed {len(response)} trips to MongoDB using bulk operations")
        logfire.info(f"✅ Updated {update_count} existing entries")
        logfire.info(f"✅ Created {create_count} new entries")
        logfire.info(f"All documents set to expire in {expiry_seconds} seconds ({REDIS_EXPIRY_HOURS} hours)")
        logfire.info(f"Total time: {elapsed_time:.2f} seconds ({ops_per_second:.2f} operations/second)")
        
    except pymongo.errors.ConnectionFailure as e:
        logfire.error(f"MongoDB connection error: {e}")
        raise
    except pymongo.errors.PyMongoError as e:
        logfire.error(f"MongoDB error during operation: {e}")
        raise
    except Exception as e:
        logfire.error(f"Unexpected error during MongoDB operation: {type(e).__name__}: {e}")
        raise
    finally:
        # Close the MongoDB connection
        if 'client' in locals():
            client.close()
            logfire.info("MongoDB connection closed successfully")


async def fetch_gtfs_stops_flow():
    """Main ETL flow that fetches GTFS data and uploads it to MongoDB"""
    logfire.info("Starting GTFS etl process")
    try:
        response = await fetch_gtfs_stops_task()
        upload_gtfs_stops_to_mongodb_task(response)
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