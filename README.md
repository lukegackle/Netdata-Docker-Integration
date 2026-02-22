![Netdata Docker Integration](/custom_components/netdata_docker/brands/icon.png)

# Netdata Docker for Home Assistant
Monitor your Docker containers in Home Assistant using data from your Netdata instance. This integration uses the Netdata `/api/v1/allmetrics` API to provide real-time container status and performance metrics with ZERO manual configuration.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)

![Homeassistant sensors screenshot](/sensor-screenshot.png)

## Features

- **Auto-Discovery**: Automatically finds and monitors all Docker containers on your Netdata host.
- **Single Entity Model**: Creates one sensor per container (e.g., `sensor.netdata_docker_nextcloud`).
- **Real-Time Status**: The primary state is the container status (`running`, `exited`, etc.).
- **Rich Attributes**: Exposes CPU %, Memory usage, Network I/O, Health Status, and PID count as attributes.
- **Friendly Name Resolution**: Automatically resolves 12-char hex IDs to human-readable container names if Netdata is configured to see them.
- **Configurable Polling**: Custom update intervals (default 30s).

## Metrics Tracked

- **State**: Container status (Running, Exited, etc.)
- **Health**: Container health status (Healthy, Unhealthy)
- **CPU**: CPU utilization % (System + User)
- **Memory**: Resident memory usage in MiB
- **Memory %**: Memory utilization percentage
- **Network**: Inbound and Outbound throughput in kilobits/s
- **PIDs**: Number of active processes

## Installation

### Via HACS (Recommended)
1. Open HACS in your Home Assistant instance.
2. Click on **Integrations**.
3. Click the three dots in the top right and select **Custom repositories**.
4. Add the URL of this repository and select **Integration** as the category.
5. Search for `Netdata Docker` and click **Download**.
6. Restart Home Assistant.

### Manual Installation
1. Download the latest release.
2. Copy the `custom_components/netdata_docker` directory to your Home Assistant `custom_components` folder.
3. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **Netdata Docker**.
3. Enter your Netdata URL (e.g., `http://192.168.1.50:19999`).
4. Select your preferred **Scan Interval** (default 30 seconds).


## Credits

Based on the original Netdata allmetrics integration, re-architected for robust Docker container monitoring in Homeassistant.
