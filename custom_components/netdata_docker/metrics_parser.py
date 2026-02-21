"""
Standalone Netdata allmetrics JSON parser for Docker container metrics.

This module has ZERO Home Assistant dependencies and can be tested
independently. It parses the JSON response from Netdata's
/api/v1/allmetrics?format=json endpoint and extracts per-container
metrics (state, health, CPU, memory, network).

Netdata reports container data using two different key patterns:

  1. docker_local.container_<name>_state / _health_status
     -> Container name is embedded directly in the key.
     -> Dimensions represent possible states; the one with value 1.0 is active.

  2. cgroup_<identifier>.<metric>
     -> Identifier may be a friendly name (e.g. "nextcloud") or a
        12-char hex Docker container ID (e.g. "0434f3dc6d06").
     -> The "name" field inside the entry may contain a renamed version
        with the friendly container name (set by Netdata's cgroup plugin).

The parser uses a three-tier name resolution strategy to map identifiers
to human-readable container names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ContainerMetrics:
    """Metrics extracted for a single Docker container."""

    name: str
    container_id: str = ""  # Short hex ID if available

    # State / health (string values like "running", "healthy")
    state: str = "unknown"
    health: str = "unknown"

    # Resource metrics (numeric)
    cpu_percent: float = 0.0
    memory_usage: float = 0.0   # MiB
    memory_limit: float = 0.0   # MiB (0 = unknown)
    memory_utilization: float = 0.0  # %
    network_rx: float = 0.0     # kilobits/s
    network_tx: float = 0.0     # kilobits/s
    pids: float = 0.0           # number of processes/pids

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a flat dictionary."""
        return {
            "name": self.name,
            "container_id": self.container_id,
            "state": self.state,
            "health": self.health,
            "cpu_percent": self.cpu_percent,
            "memory_usage": self.memory_usage,
            "memory_limit": self.memory_limit,
            "memory_utilization": self.memory_utilization,
            "network_rx": self.network_rx,
            "network_tx": self.network_tx,
            "pids": self.pids,
        }


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# docker_local.container_<name>_state  or  _health_status
_RE_DOCKER_STATE = re.compile(
    r"docker_local\.container_(.+?)_state$"
)
_RE_DOCKER_HEALTH = re.compile(
    r"docker_local\.container_(.+?)_health_status$"
)

# cgroup_<identifier>.<metric>
_RE_CGROUP = re.compile(
    r"^cgroup_(.+?)\.(.+)$"
)

# Detect 12+ char lowercase hex strings (Docker short IDs)
_RE_HEX_ID = re.compile(r"^[0-9a-f]{12,}$")


def _is_hex_id(s: str) -> bool:
    """Return True if *s* looks like a Docker container short ID."""
    return bool(_RE_HEX_ID.match(s))


def _safe_dim_value(dims: dict, key: str, default: float = 0.0) -> float:
    """Safely extract a numeric value from a dimensions dict."""
    dim = dims.get(key)
    if dim is None:
        return default
    val = dim.get("value") if isinstance(dim, dict) else dim
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _active_dimension(dims: dict) -> str | None:
    """Return the name of the dimension whose value is 1.0 (active state)."""
    for dim_id, dim_data in dims.items():
        if isinstance(dim_data, dict) and dim_data.get("value") == 1.0:
            return dim_data.get("name", dim_id)
    return None


# ---------------------------------------------------------------------------
# Name resolution
# ---------------------------------------------------------------------------

def _build_name_map(data: dict) -> dict[str, str]:
    """Build a mapping from hex container IDs to friendly names.

    Scans ALL entries looking for cgroup entries where the ``name`` field
    contains a friendly (non-hex) version of the identifier.  For example
    the key ``cgroup_0434f3dc6d06.cpu`` might have
    ``"name": "cgroup_nextcloud.cpu"`` when Netdata's cgroup renaming is
    active.
    """
    id_to_name: dict[str, str] = {}

    for key, details in data.items():
        m = _RE_CGROUP.match(key)
        if not m:
            continue

        raw_id = m.group(1)
        if not _is_hex_id(raw_id):
            # Already has a friendly name in the key — no mapping needed
            continue

        # Check the "name" field for a renamed version.
        # This is the ONLY reliable source for friendly names.
        # The "family" and "title" fields contain generic metric-family
        # names like "eth0", "cpu", "mem", etc. and must NOT be used.
        name_field = details.get("name", "")
        m2 = _RE_CGROUP.match(name_field)
        if m2:
            candidate = m2.group(1)
            if candidate != raw_id and not _is_hex_id(candidate):
                # We found a friendly name!
                if raw_id not in id_to_name or len(candidate) > len(id_to_name[raw_id]):
                    id_to_name[raw_id] = candidate

    # Also extract names from docker_local entries
    for key in data:
        m = _RE_DOCKER_STATE.match(key)
        if not m:
            m = _RE_DOCKER_HEALTH.match(key)
        if m:
            container_name = m.group(1)
            # This gives us a known container name; we can try to match
            # it to hex IDs later if needed
            # For now, these are handled directly in the discovery phase.
            pass

    return id_to_name


# ---------------------------------------------------------------------------
# Container discovery
# ---------------------------------------------------------------------------

def discover_containers(data: dict) -> dict[str, ContainerMetrics]:
    """Parse Netdata allmetrics JSON and return per-container metrics.

    Parameters
    ----------
    data : dict
        The full JSON response from
        ``/api/v1/allmetrics?format=json``.

    Returns
    -------
    dict[str, ContainerMetrics]
        Mapping of container display-name → metrics.
    """
    name_map = _build_name_map(data)
    containers: dict[str, ContainerMetrics] = {}

    def _resolve(raw_id: str) -> str:
        """Resolve a raw identifier to its display name."""
        if not _is_hex_id(raw_id):
            return raw_id
        return name_map.get(raw_id, raw_id[:12])

    def _get_or_create(display_name: str, raw_id: str = "") -> ContainerMetrics:
        if display_name not in containers:
            containers[display_name] = ContainerMetrics(
                name=display_name,
                container_id=raw_id if _is_hex_id(raw_id) else "",
            )
        cm = containers[display_name]
        # Update container_id if we now have a hex id
        if raw_id and _is_hex_id(raw_id) and not cm.container_id:
            cm.container_id = raw_id
        return cm

    # ----- Pass 1: docker_local state and health_status entries -----
    for key, details in data.items():
        dims = details.get("dimensions", {})

        m = _RE_DOCKER_STATE.match(key)
        if m:
            name = m.group(1)
            cm = _get_or_create(name)
            active = _active_dimension(dims)
            if active:
                cm.state = active
            continue

        m = _RE_DOCKER_HEALTH.match(key)
        if m:
            name = m.group(1)
            cm = _get_or_create(name)
            active = _active_dimension(dims)
            if active:
                cm.health = active
            continue

    # ----- Pass 2: cgroup entries (resource metrics) -----
    for key, details in data.items():
        m = _RE_CGROUP.match(key)
        if not m:
            continue

        raw_id = m.group(1)
        metric_part = m.group(2)
        dims = details.get("dimensions", {})

        display_name = _resolve(raw_id)
        cm = _get_or_create(display_name, raw_id)

        # CPU: cgroup_<id>.cpu
        if metric_part == "cpu":
            user = _safe_dim_value(dims, "user")
            system = _safe_dim_value(dims, "system")
            cm.cpu_percent = round(user + system, 2)

        # Memory usage: cgroup_<id>.mem_usage (in MiB typically)
        elif metric_part == "mem_usage":
            ram = _safe_dim_value(dims, "ram")
            if ram == 0.0:
                # Fallback: try "mem" dimension or top-level value
                ram = _safe_dim_value(dims, "mem")
            if ram == 0.0:
                val = details.get("value")
                if val is not None:
                    try:
                        ram = float(val)
                    except (ValueError, TypeError):
                        pass
            cm.memory_usage = round(ram, 2)

        # Memory limit: cgroup_<id>.mem_usage_limit
        elif metric_part == "mem_usage_limit":
            limit = _safe_dim_value(dims, "limit")
            if limit == 0.0:
                val = details.get("value")
                if val is not None:
                    try:
                        limit = float(val)
                    except (ValueError, TypeError):
                        pass
            cm.memory_limit = round(limit, 2)

        # Memory utilization: cgroup_<id>.mem_utilization
        elif metric_part == "mem_utilization":
            util = _safe_dim_value(dims, "utilization")
            if util == 0.0:
                val = details.get("value")
                if val is not None:
                    try:
                        util = float(val)
                    except (ValueError, TypeError):
                        pass
            cm.memory_utilization = round(util, 2)

        # Network: cgroup_<id>.net_eth0 (or net_<ifname>)
        elif metric_part.startswith("net_") and metric_part.count("_") == 1:
            # Only the primary bandwidth metric (e.g. net_eth0), not
            # net_packets_eth0, net_drops_eth0, etc.
            iface = metric_part.split("_", 1)[1]
            rx = _safe_dim_value(dims, "received")
            tx = abs(_safe_dim_value(dims, "sent"))
            # Accumulate if multiple interfaces
            cm.network_rx = round(cm.network_rx + rx, 2)
            cm.network_tx = round(cm.network_tx + tx, 2)

        # PIDs: cgroup_<id>.pids_current
        elif metric_part == "pids_current":
            pids = _safe_dim_value(dims, "pids")
            if pids == 0.0:
                val = details.get("value")
                if val is not None:
                    try:
                        pids = float(val)
                    except (ValueError, TypeError):
                        pass
            cm.pids = pids

    # ----- Filter: Only keep entries that look like real containers -----
    # A real container should have at least one of: state, cpu, or memory data
    filtered: dict[str, ContainerMetrics] = {}
    for name, cm in containers.items():
        has_state = cm.state != "unknown"
        has_resources = cm.cpu_percent > 0 or cm.memory_usage > 0
        if has_state or has_resources:
            filtered[name] = cm

    return filtered
