#!/usr/bin/env python3
"""
Continuous runner for GTFS ETL process.
This script runs the ETL process at regular intervals.
"""
import asyncio
import time
import os
import sys
import logfire
from gtfs_stops import fetch_gtfs_stops_flow

# Get the interval from environment variable, default to 60 seconds (1 minute)
RUN_INTERVAL_SECONDS = int(os.environ.get('RUN_INTERVAL_SECONDS', '60'))

logfire.info(f"Starting continuous GTFS ETL runner with interval: {RUN_INTERVAL_SECONDS} seconds")


async def run_continuously():
    """Run the ETL process continuously at regular intervals"""
    iteration = 0

    while True:
        iteration += 1
        logfire.info(f"=== Starting ETL iteration #{iteration} ===")

        start_time = time.time()

        try:
            success = await fetch_gtfs_stops_flow()

            elapsed_time = time.time() - start_time

            if success:
                logfire.info(f"✅ Iteration #{iteration} completed successfully in {elapsed_time:.2f} seconds")
            else:
                logfire.error(f"❌ Iteration #{iteration} failed after {elapsed_time:.2f} seconds")

        except Exception as e:
            elapsed_time = time.time() - start_time
            logfire.error(f"❌ Unhandled error in iteration #{iteration} after {elapsed_time:.2f} seconds: {type(e).__name__}: {e}")

        # Calculate sleep time to maintain consistent interval
        sleep_time = max(0, RUN_INTERVAL_SECONDS - (time.time() - start_time))

        if sleep_time > 0:
            logfire.info(f"Waiting {sleep_time:.2f} seconds until next run...")
            await asyncio.sleep(sleep_time)
        else:
            logfire.warning(f"ETL process took longer than interval ({elapsed_time:.2f}s > {RUN_INTERVAL_SECONDS}s), starting next iteration immediately")


if __name__ == "__main__":
    try:
        asyncio.run(run_continuously())
    except KeyboardInterrupt:
        logfire.info("Received shutdown signal, stopping continuous runner...")
        sys.exit(0)
    except Exception as e:
        logfire.error(f"Fatal error in continuous runner: {type(e).__name__}: {e}")
        sys.exit(1)
