import aiohttp
import pytz
from datetime import datetime
from google.transit import gtfs_realtime_pb2
import logfire
import os
import sys
import warnings

# Configure logfire with token from environment variable
logfire.configure(token="pylf_v1_us_r8nwb7ycg8bSxsSnjktwMJ1cV3s0sLlwTvCNvdNTpm8ngrep")
async def fetch_trip_updates():
    """
    Asynchronously fetches GTFS real-time trip updates from the Translink API.

    This function sends a GET request to the Translink API endpoint for SEQ (South East Queensland)
    trip updates and returns the raw response data.

    Returns:
        bytes: The raw response data containing GTFS real-time trip updates.

    Raises:
        aiohttp.ClientError: If there's an error in making the HTTP request or receiving the response.
    """
    logfire.info("Fetching trip updates from Translink API...")
    url = "https://gtfsrt.api.translink.com.au/api/realtime/SEQ/TripUpdates"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.read()
            logfire.info(f"Received response from API with status: {response.status}")
            return data


async def process_entity_trip_updates(entity):
    """
    Process GTFS real-time trip updates for a single entity.

    This function parses the given entity data, extracts relevant trip and stop information,
    and returns a list of dictionaries containing details about each stop update.

    Args:
        entity (FeedEntity): GTFS real-time entity data.

    Returns:
        list: A list of dictionaries, where each dictionary contains information about
        a stop update for a specific trip.
    """
    stop_updates = []
    if entity.HasField('trip_update'):
        trip_id = entity.trip_update.trip.trip_id
        if 'SBL' not in trip_id:
            return stop_updates
        
        route_id = entity.trip_update.trip.route_id
        
        for stop in entity.trip_update.stop_time_update:
            stop_info = {
                'trip_id': trip_id,
                'route_id': route_id,
                'stop_id': stop.stop_id,
                'departure_delay': stop.departure.delay if stop.HasField('departure') else None,
                'departure_time': datetime.fromtimestamp(stop.departure.time, tz=pytz.UTC).astimezone(pytz.timezone('Australia/Brisbane')).strftime('%Y-%m-%d %H:%M:%S') if stop.HasField('departure') else None,
                'stop_sequence': stop.stop_sequence
            }
            stop_updates.append(stop_info)

    return stop_updates



async def fetch_and_process_trip_updates():
    """
    Fetches and processes GTFS real-time trip updates.

    This function performs the following steps:
    1. Fetches raw GTFS real-time data from the API.
    2. Parses the fetched data into a FeedMessage object.
    3. Processes each entity in the feed concurrently.
    4. Collects and organizes the processed data into stop updates.
    5. Transforms the data to group stops by trip_id and route_id.
    6. Filters to include only the minimum stop sequence and the next one for each trip.

    Returns:
        list: A list of dictionaries where each dictionary contains trip_id, route_id,
              and a list of stops with their respective stop_id, departure_delay, and departure_time.

    Note:
        This function filters for trips with 'SBL' in their trip_id and uses the
        Brisbane timezone for time conversions.
    """
    logfire.info("Starting GTFS data fetch and processing")
    content = await fetch_trip_updates()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    logfire.info(f"Parsed feed with {len(feed.entity)} entities")
    
    # Process entities directly instead of creating tasks
    stop_updates = []
    sbl_count = 0
    for entity in feed.entity:
        entity_stop_updates = await process_entity_trip_updates(entity)
        if entity_stop_updates:
            stop_updates.extend(entity_stop_updates)
            sbl_count += 1
    
    logfire.info(f"Processed {sbl_count} SBL trips out of {len(feed.entity)} total entities")
    logfire.info(f"Total stop updates collected: {len(stop_updates)}")

    # Transform the data to group stops by trip_id and route_id
    logfire.info("Transforming data to group stops by trip_id and route_id")
    transformed_data = {}
    for update in stop_updates:
        trip_id = update['trip_id']
        route_id = update['route_id']
        stop_sequence = update['stop_sequence']
        key = (trip_id, route_id)
        
        if key not in transformed_data:
            transformed_data[key] = {
                'trip_id': trip_id,
                'route_id': route_id,
                'stops': []
            }
        
        stop_info = {
            'stop_id': update['stop_id'],
            'departure_delay': update['departure_delay'],
            'departure_time': update['departure_time'],
            'stop_sequence': stop_sequence
        }
        
        transformed_data[key]['stops'].append(stop_info)
    
    logfire.info(f"Grouped data into {len(transformed_data)} unique trip_id/route_id combinations")
    
    # Filter to include only the minimum stop sequence and the next one for each trip
    logfire.info("Filtering to include only min stop sequence and next one")
    for key in transformed_data:
        trip_id, route_id = key
        stops = transformed_data[key]['stops']
        
        # Sort stops by stop_sequence
        stops.sort(key=lambda x: x['stop_sequence'])
        
        # Keep only the minimum stop sequence and the next one (if available)
        if len(stops) > 0:
            min_sequence = stops[0]['stop_sequence']
            filtered_stops = [stops[0]]
            
            # Add the next stop sequence if available
            for stop in stops[1:]:
                if stop['stop_sequence'] == min_sequence + 1:
                    filtered_stops.append(stop)
                    break
            
            transformed_data[key]['stops'] = filtered_stops
    
    # Convert the dictionary to a list
    result = list(transformed_data.values())
    
    logfire.info(f"Processing complete: {len(result)} trips with filtered stops")
    return result



