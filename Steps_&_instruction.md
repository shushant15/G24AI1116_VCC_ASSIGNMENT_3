# Step-by-Step Guide: Local VM Setup, Monitoring, and Auto-Scaling to GCP

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Step 1: Create a Local VM using VirtualBox](#step-1-create-a-local-vm-using-virtualbox)
4. [Step 2: Implement Resource Monitoring Using Grafana and Prometheus](#step-2-implement-resource-monitoring-using-grafana-and-prometheus)
5. [Step 3: Install and Configure Node Exporter](#step-3-install-and-configure-node-exporter)
6. [Step 4: Install and Configure Grafana](#step-4-install-and-configure-grafana)
7. [Step 5: Create a Dashboard for CPU, Memory, and Disk Usage](#step-5-create-a-dashboard-for-cpu-memory-and-disk-usage)
8. [Step 6: Configure Auto-Scaling on GCP](#step-6-configure-auto-scaling-on-gcp)
9. [Step 7: Deploy a Sample Application](#step-7-deploy-a-sample-application)
10. [Step 8: Automate Resource Migration](#step-8-automate-resource-migration)
11. [Step 9: Demonstrating Auto-Scaling and Resource Migration](#step-9-demonstrating-auto-scaling-and-resource-migration)
12. [Conclusion](#conclusion)

## Introduction
This guide provides a comprehensive step-by-step approach to setting up a local Fedora VM using VirtualBox, implementing monitoring with Grafana and Prometheus, and configuring auto-scaling with Google Cloud Platform (GCP). By following this guide, you will be able to automatically migrate resources to the cloud when the local VM exceeds a CPU usage threshold of 75%.

## Prerequisites
Before proceeding, ensure you have the following:
- A system with VirtualBox installed
- Fedora Server ISO
- Basic knowledge of Linux commands
- A Google Cloud Platform (GCP) account
- Installed `gcloud` CLI with authenticated access

## Step 1: Create a Local VM using VirtualBox
We will use VirtualBox to create a local Fedora VM.

### 1.1 Install VirtualBox and Fedora
- Download and install VirtualBox from [VirtualBox Official Site](https://www.virtualbox.org/).
- Download Fedora Server ISO from [Fedora Official Site](https://getfedora.org/).
- Open VirtualBox and create a new VM:
  - Click **New** → Name it (e.g., `localvm`).
  - Select **Linux** → **Fedora (64-bit)**.
  - Assign **RAM (4GB or more)**.
  - Create a **Virtual Hard Disk (20GB or more)**.
  - Select **Dynamically Allocated Storage** and create the disk.

### 1.2 Install Fedora on the VM
- Start the VM and select the downloaded Fedora ISO.
- Follow the installation process.
- After installation, reboot and log in.

### 1.3 Install Essential Packages
Run the following commands:

```sh
sudo dnf update -y
sudo dnf install -y curl wget git gcc make
sudo dnf install -y openssh-server
sudo systemctl enable --now sshd
```

---

## Step 2: Implement Resource Monitoring Using Grafana and Prometheus
We will use Prometheus to collect metrics and Grafana for visualization.

### 2.1 Install Prometheus
Run:

```sh
wget https://github.com/prometheus/prometheus/releases/download/v3.2.1/prometheus-3.2.1.linux-386.tar.gz
tar -xvf prometheus-3.2.1.linux-386.tar.gz
cd prometheus-2.45.0.linux-amd64
sudo mv prometheus /usr/local/bin/
sudo mv promtool /usr/local/bin/
```

### 2.2 Configure Prometheus
Create a Prometheus configuration file:

```sh
sudo mkdir /etc/prometheus
sudo nano /etc/prometheus/prometheus.yml
```

(Add the YAML configuration and save the file.)

### 2.3 Create a Prometheus Service
Run:

```sh
sudo nano /etc/systemd/system/prometheus.service
```

(Add the service configuration and save the file.)

Start Prometheus:

```sh
sudo systemctl daemon-reload
sudo systemctl start prometheus
sudo systemctl enable prometheus
```
- Note: If Prometheus is not loading when trying to check http://localhost:9090, use below steps(in OS Linux):
  ```sh
  sestatus
  sudo setenforce 0
  sudo systemctl restart prometheus
  ``` 
---

## Step 3: Install and Configure Node Exporter
Node Exporter helps collect system metrics.

### 3.1 Install Node Exporter
Run:

```sh
wget https://github.com/prometheus/node_exporter/releases/download/v1.9.0/node_exporter-1.9.0.linux-386.tar.gz
tar -xvf node_exporter-1.9.0.linux-386.tar.gz
cd node_exporter-1.9.0.linux-386
sudo mv node_exporter /usr/local/bin/
```

### 3.2 Create a Node Exporter Service
Run:

```sh
sudo nano /etc/systemd/system/node_exporter.service
```

(Add the service configuration and save the file.)

Start Node Exporter:

```sh
sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter
```

---

## Step 4: Install and Configure Grafana
### 4.1 Install Grafana
Run:

```sh
sudo dnf install -y grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

Access Grafana at [http://localhost:3000](http://localhost:3000) (Default login: **admin/admin**).

### 4.2 Add Prometheus as a Data Source
- Go to **Grafana → Configuration → Data Sources**.
- Select **Prometheus**.
- Set **URL** to: `http://localhost:9090`.
- Click **Save & Test**.

---

## Step 5: Create a Dashboard for CPU, Memory, and Disk Usage
- Go to **Grafana → Create → Dashboard**.
- Click **Add a New Panel**.

### 5.1 CPU Usage Panel
Add Query:

```promql
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

Set Visualization to **Gauge** or **Graph**.

### 5.2 Memory Usage Panel
Add Query:

```promql
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

Set Visualization to **Gauge** or **Graph**.

### 5.3 Disk Usage Panel
Add Query:

```promql
100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})
```

Set Visualization to **Bar Chart**. Click **Apply and Save** the Dashboard.

---

## Step 6: Configure Auto-Scaling on GCP
### 6.1 Set Up GCP Environment
- Create the repository file:
```sh
sudo tee /etc/yum.repos.d/google-cloud-sdk.repo << EOL
[google-cloud-sdk]
name=Google Cloud SDK
baseurl=https://packages.cloud.google.com/yum/repos/cloud-sdk-el9-x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=0
gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg
EOL

```
-  Clean and refresh repositories:
```sh
sudo dnf clean all
sudo dnf makecache
```

- Install Google Cloud SDK and verify version
```sh
sudo dnf install -y google-cloud-sdk
gcloud --version
```

- Initialize Google Cloud SDK
```sh
gcloud init
```

### 6.2 Create a Compute Engine VM in GCP using sdk from local vm
```sh
gcloud compute instances create gcp-vm \
  --machine-type=e2-medium \
  --image-family=fedora-cloud \
  --image-project=fedora-cloud \
  --zone=us-central1-a
```

### 6.3 Configure Auto-Scaling
- Login to GCP UI platform
- Now, Create a instance Templates(Eg: web-template) which will be used in the Managed Instance Group
- Now, Create a Managed Instance Group with Debian VMs (Eg: web-migration)
- Provide the minimum (like 1) VM instnaces and maximum(like 10) VM instnaces
- Provide the policy- CPU usgae more than 75%, should trigger the auto scaling
- Configure Auto-Scaling on the Managed Instance Group and save the managed instance group and check the new instance in compute engine

---

## Step 7: Deploy a Sample Application
Application to show the hostname and it's ip, wherever the script will be running
### 7.1 Install Flask
```sh
pip install flask
```

### 7.2 Create a Sample App using(like using python and flask)
- create the directories
```sh
mkdir -p /home/user/app
nano /home/user/app/app.py
```
- Code snippet attached with file

### 7.3 Make the script executable 
```sh
chmod +x ~/app/app.py
```

### 7.4 Execute the application
```sh
python3 ~/app/app.py
```

### 7.5 Additionally if the application needs to be kept it running in the background
```sh
nohup python3 ~/app/app.py > ~/app/app.log 2>&1 &
```
- Check the ip address and hostname of the local VM

---

## Step 8: Automate Resource Migration
We may automate with below:
- custom python code snippet which will use the python subprocess and os libraries to get CPU usage
- a python script which will use the prometheus to check the CPU usage by getting the mertics

## 8.1 Create Migration Script
- create the directories
```sh 
mkdir -p /home/user/migration
nano /home/user/migration/migration_script.py
```

- Use the code snippet the as per the choice and application

### 8.2 Make the script executable
```sh
chmod +x /home/user/migration/migration_script.py
```

### 8.3 Run the script manually:
```sh
python3 /home/user/migration/migration_script.py
```

### 8.4 To run it automatically at startup, add it to crontab
```sh
crontab -e
@reboot /usr/bin/python3 /home/user/migration/migration_script.py &
```

---

## Step 9: Demonstrating Auto-Scaling and Resource Migration
### 9.1 Simulate High CPU Usage on Local VM
To trigger 75% CPU usage, run a CPU stress test:

```sh
sudo dnf install -y stress
stress --cpu 4 --timeout 300
```

### 9.2 Monitor CPU Usage in Grafana
- Open Grafana at [http://localhost:3000](http://localhost:3000).
- Check **CPU Usage Panel**.
- Wait until CPU exceeds 75% for at least **10 seconds**.

### 9.3 Trigger GCP Migration Automatically
- The **migration script** continuously checks CPU usage.
- Once CPU exceeds 75%, it spawns a new VM in GCP.

If the script is not running, start it manually:

```sh
python3 /home/user/migration/migration_script.py
```

### 9.4 Verify GCP VM is Running
- Check running instances:

```sh
gcloud compute instances list
```

- If the instance is running, access it via SSH:

```sh
gcloud compute ssh migrated-instance --zone=us-central1-a
```

- Check if the application is running:

```sh
curl http://localhost:5000
```

Expected Output:

```sh
Hello from VM running on {host_name} (IP: {host_ip})
```

### 9.5 Simulate Low CPU Usage to Trigger Scale-Down
To stop auto-scaling and remove the extra GCP VM:

- Kill CPU stress test on the local VM:

```sh
pkill stress
```

- Wait for CPU usage to drop below 75% (Grafana will show the decrease).
- The auto-scaler will **terminate the GCP VM automatically**.

- Check instance deletion:

```sh
gcloud compute instances list
```

- If the GCP VM is no longer listed, **auto-scaling down was successful!**

---

## Conclusion
By following this guide, you have successfully:
- Set up a local Fedora VM using VirtualBox.
- Installed and configured Prometheus and Grafana for monitoring.
- Created dashboards to visualize system metrics.
- Configured Google Cloud Platform for auto-scaling and migration.
- Deployed a sample application and automated its migration when CPU usage exceeded a threshold.

This setup ensures that resources are efficiently utilized, and applications remain available even during high resource demands. You can further expand on this by integrating more monitoring tools or optimizing auto-scaling policies. Happy coding!

