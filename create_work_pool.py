import os
from prefect.client import get_client
import asyncio

async def create_work_pool():
    # Create a Prefect client
    client = get_client()
    
    # Define the work pool configuration
    work_pool_name = "gtfs-pool"
    work_pool_config = {
        "name": work_pool_name,
        "type": "managed",
        "base_job_template": {
            "job_configuration": {
                "env": {
                    "PREFECT_LOGGING_LEVEL": "INFO"
                }
            }
        },
        "paused": False,
        "description": "Managed work pool for GTFS ETL flows"
    }
    
    # Check if the work pool already exists
    work_pools = await client.read_work_pools()
    
    if work_pool_name not in [wp.name for wp in work_pools]:
        print(f"Creating work pool: {work_pool_name}")
        await client.create_work_pool(**work_pool_config)
        print(f"Work pool '{work_pool_name}' created successfully!")
    else:
        print(f"Work pool '{work_pool_name}' already exists.")
    
    # Print all available work pools
    work_pools = await client.read_work_pools()
    print("\nAvailable work pools:")
    for wp in work_pools:
        print(f"- {wp.name} ({wp.type})")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(create_work_pool()) 