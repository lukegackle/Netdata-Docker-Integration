"""Constants for the Netdata Docker integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "netdata_docker"
CONF_URL = "url"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_POLL_INTERVAL = 30

# Metric type identifiers (used for attribute mapping)
METRIC_STATUS = "state"
METRIC_HEALTH = "health"
METRIC_CPU = "cpu_percent"
METRIC_MEMORY = "memory_usage"
METRIC_MEMORY_LIMIT = "memory_limit"
METRIC_MEMORY_UTILIZATION = "memory_utilization"
METRIC_NETWORK_RX = "network_rx"
METRIC_NETWORK_TX = "network_tx"
METRIC_PIDS = "pids"

# Attributes to expose (key in ContainerMetrics -> attribute name)
ATTR_MAP = {
    METRIC_HEALTH: "health_status",
    METRIC_CPU: "cpu_percent",
    METRIC_MEMORY: "memory_usage_mib",
    METRIC_MEMORY_LIMIT: "memory_limit_mib",
    METRIC_MEMORY_UTILIZATION: "memory_utilization_percent",
    METRIC_NETWORK_RX: "network_rx_kbps",
    METRIC_NETWORK_TX: "network_tx_kbps",
    METRIC_PIDS: "pids",
}
