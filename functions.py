import aiohttp
import pytz
from datetime import datetime
from google.transit import gtfs_realtime_pb2
import logfire

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
        # Check if trip_id contains either 'SBL' or 'SUN'
        if 'SBL' not in trip_id and 'SUN' not in trip_id:
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
        This function filters for trips with either 'SBL' or 'SUN' in their trip_id and uses the
        Brisbane timezone for time conversions.
    """
    logfire.info("Starting GTFS data fetch and processing")
    content = await fetch_trip_updates()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(content)
    logfire.info(f"Parsed feed with {len(feed.entity)} entities")
    
    # Process entities directly instead of creating tasks
    stop_updates = []
    filtered_count = 0
    for entity in feed.entity:
        entity_stop_updates = await process_entity_trip_updates(entity)
        if entity_stop_updates:
            stop_updates.extend(entity_stop_updates)
            filtered_count += 1
    
    logfire.info(f"Processed {filtered_count} SBL/SUN trips out of {len(feed.entity)} total entities")
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
    
    # Get current time in Brisbane timezone
    brisbane_tz = pytz.timezone('Australia/Brisbane')
    now_brisbane = datetime.now(brisbane_tz)
    logfire.info(f"Current Brisbane time for filtering: {now_brisbane.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

    # Filter to include only the minimum stop sequence and the next one, AND filter by current time
    logfire.info("Filtering stops by sequence and departure time...")
    final_filtered_data = {}
    stops_removed_by_time = 0
    
    for key, trip_data in transformed_data.items():
        trip_id, route_id = key
        stops = trip_data['stops']
        
        # Sort stops by stop_sequence
        stops.sort(key=lambda x: x['stop_sequence'])
        
        sequence_filtered_stops = []
        # Keep only the minimum stop sequence and the next one (if available)
        if len(stops) > 0:
            min_sequence = stops[0]['stop_sequence']
            sequence_filtered_stops.append(stops[0])
            
            # Add the next stop sequence if available
            for stop in stops[1:]:
                if stop['stop_sequence'] == min_sequence + 1:
                    sequence_filtered_stops.append(stop)
                    break
        
        # Filter by departure time
        time_filtered_stops = []
        for stop in sequence_filtered_stops:
            if stop['departure_time']:
                # Parse departure time string back to datetime object
                # Assuming the string format is '%Y-%m-%d %H:%M:%S' and represents Brisbane time
                try:
                    departure_dt_str = stop['departure_time']
                    # Naive datetime object representing Brisbane time
                    departure_dt_naive = datetime.strptime(departure_dt_str, '%Y-%m-%d %H:%M:%S')
                    # Localize it to Brisbane timezone
                    departure_dt_aware = brisbane_tz.localize(departure_dt_naive) 
                    
                    if departure_dt_aware <= now_brisbane:
                        time_filtered_stops.append(stop)
                    else:
                        stops_removed_by_time += 1
                except ValueError as e:
                    logfire.error(f"Error parsing departure time '{stop['departure_time']}' for trip {trip_id}, stop {stop['stop_id']}: {e}")
                    # Optionally decide whether to keep/discard stops with unparseable times
            else:
                 # Handle cases where departure_time is None if necessary, e.g., keep them or discard them
                 # Currently, they are implicitly discarded by the check `if stop['departure_time']:`
                 pass 

        # Only keep the trip if it still has stops after time filtering
        if time_filtered_stops:
            final_filtered_data[key] = {
                'trip_id': trip_id,
                'route_id': route_id,
                'stops': time_filtered_stops
            }

    logfire.info(f"Removed {stops_removed_by_time} stops due to future departure times.")
    
    # Convert the dictionary to a list
    result = list(final_filtered_data.values())
    
    logfire.info(f"Processing complete: {len(result)} trips remaining after all filters")
    return result



