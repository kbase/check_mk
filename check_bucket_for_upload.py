#!/usr/bin/env python
from google.cloud import storage
from datetime import datetime, timedelta, timezone
import re
import os
import sys

# Set the default path for the service account key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/root/check_mk/gcp_key.json"


def check_recent_file(bucket_name, days_threshold, file_path, file_pattern):
    client = storage.Client()
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    pattern = re.compile(file_pattern)
    recent_file_found = False
    recent_file_name = None
    for blob in client.list_blobs(bucket_name, prefix=file_path):
        # Only consider files matching the specified pattern
        if pattern.search(blob.name) and blob.updated > threshold_date:
            recent_file_found = True
            recent_file_name = blob.name
            break

    # Return status based on whether a recent file was found
    if recent_file_found:
        print(f"OK - Recent file '{recent_file_name}' found in '{file_path}' within the last {days_threshold} days.")
        sys.exit(0)
    else:
        print(f"CRITICAL - No file matching pattern '{file_pattern}' in '{file_path}' uploaded to GCP in the last {days_threshold} days.")
        sys.exit(2)


# Default configurations
default_bucket_name = "spin2"
default_days_threshold = 7
default_file_path = "backups/homology/assemblyhomologyservice-mongo"
default_file_pattern = r"\d{4}-\d{2}-\d{2}\.tar\.gz$"

# Parse command-line arguments
bucket_name = sys.argv[1] if len(sys.argv) > 1 else default_bucket_name
days_threshold = int(sys.argv[2]) if len(sys.argv) > 2 else default_days_threshold
file_path = sys.argv[3] if len(sys.argv) > 3 else default_file_path
file_pattern = sys.argv[4] if len(sys.argv) > 4 else default_file_pattern

# Run the check
check_recent_file(bucket_name, days_threshold, file_path, file_pattern)
