from gtfs_stops import fetch_gtfs_stops_flow
from datetime import timedelta
from prefect.deployments import DeploymentImage

if __name__ == "__main__":
    # Create a deployment using the flow's deploy method
    deployment = fetch_gtfs_stops_flow.deploy(
        name="gtfs-stops-flow",
        work_pool_name="Main",
        # Use the local code storage option
        image=DeploymentImage(
            name="gtfs-stops-image",
            # This tells Prefect to use the local code
            type="process",
        ),
        job_variables={
            "env": {
                "PREFECT_LOGGING_LEVEL": "INFO",
            },
            "requirements_file": "requirements.txt",  # This ensures dependencies are installed at runtime
        },
        description="GTFS Stops Flow that fetches and processes GTFS stop updates",
        tags=["gtfs", "etl", "main-kinetic", "default"],
    )
    
    print(f"Deployment created successfully!")
    print(f"Deployment name: gtfs-stops-flow")
    print(f"Work pool: Main")
    print(f"Schedule: Every 360 seconds (6 minutes)") 