import pymongo
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection details from environment variables
MONGO_USERNAME = os.environ.get('MONGO_USERNAME')
MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD')
MONGO_URI = os.environ.get('MONGO_URI', f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@cluster0.dsh19.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'gtfs_data')

def create_trips_stops_collection():
    """
    Create a collection called trips_stops in the gtfs_data database if it doesn't exist.
    """
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(MONGO_URI)
        
        # Test the connection
        server_info = client.server_info()
        print(f"Successfully connected to MongoDB at {MONGO_URI}")
        print(f"MongoDB server version: {server_info.get('version', 'unknown')}")
        
        # Access the database
        db = client[MONGO_DB_NAME]
        
        # Create the trips_stops collection if it doesn't exist
        if "trips_stops" not in db.list_collection_names():
            db.create_collection("trips_stops")
            print(f"Created 'trips_stops' collection in database '{MONGO_DB_NAME}'")
        else:
            print(f"Collection 'trips_stops' already exists in database '{MONGO_DB_NAME}'")
        
        # List collections in the database to confirm
        collections = db.list_collection_names()
        print(f"Collections in '{MONGO_DB_NAME}': {collections}")
        
        return db["trips_stops"]
    
    except pymongo.errors.ConnectionFailure as e:
        print(f"MongoDB connection error: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        raise
    finally:
        # Close the MongoDB connection if it was established
        if 'client' in locals():
            client.close()
            print("MongoDB connection closed")

if __name__ == "__main__":
    create_trips_stops_collection()
