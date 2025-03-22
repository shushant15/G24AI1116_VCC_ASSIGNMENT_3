import requests
import time
import logging
from google.cloud import compute_v1

# Configure Logging
logging.basicConfig(
    filename="/home/vm1/migration/migration.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

# Prometheus API Endpoint
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"
CPU_USAGE_QUERY = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'

# GCP Configuration (Manually Set)
PROJECT_ID = "vcc-assignment3-452401"  # Replace with your GCP project ID
ZONE = "asia-south2-a"  # Replace with your zone
INSTANCE_GROUP_NAME = "instance-group-1"  # Replace with your actual instance group name

def get_cpu_usage():
    """Fetches CPU usage from Prometheus API"""
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": CPU_USAGE_QUERY})
        response.raise_for_status()  # Ensure request was successful
        data = response.json()
        if "data" in data and "result" in data["data"] and len(data["data"]["result"]) > 0:
            return float(data["data"]["result"][0]["value"][1])
    except requests.exceptions.RequestException as e:
        logging.error(f"🚨 Error fetching CPU usage: {e}")
    return None

def scale_managed_instance_group():
    """Scales the Managed Instance Group (MIG) by increasing the instance count"""
    instance_group_client = compute_v1.InstanceGroupManagersClient()

    try:
        # Get current instance group size
        mig = instance_group_client.get(
            project=PROJECT_ID, zone=ZONE, instance_group_manager=INSTANCE_GROUP_NAME
        )
        current_size = mig.target_size

        # Increase instance count by 1
        new_size = current_size + 1
        request = compute_v1.ResizeInstanceGroupManagerRequest(
            project=PROJECT_ID,
            zone=ZONE,
            instance_group_manager=INSTANCE_GROUP_NAME,
            size=new_size
        )

        instance_group_client.resize(request=request)
        logging.info(f"🚀 Scaling Managed Instance Group '{INSTANCE_GROUP_NAME}' from {current_size} to {new_size} instances.")
    except Exception as e:
        logging.error(f"🚨 Failed to scale MIG '{INSTANCE_GROUP_NAME}': {e}")

def monitor_and_scale():
    """Monitors CPU usage and triggers scaling if usage > 75%"""
    while True:
        cpu_usage = get_cpu_usage()
        if cpu_usage is not None:
            logging.info(f"CPU Usage: {cpu_usage}%")
            if cpu_usage > 75:
                logging.warning("High CPU Usage Detected! Scaling Managed Instance Group...")
                scale_managed_instance_group()
                break  # Stop monitoring after scaling
        time.sleep(10)  # Check every 10 seconds

if __name__ == "__main__":
    logging.info("Starting Migration Monitor for Managed Instance Group Scaling...")
    monitor_and_scale()

