"""
Comprehensive standalone tests for the Netdata Docker metrics parser.

These tests run WITHOUT Home Assistant — they validate the pure-Python
metrics_parser module directly.

Run with:
    cd c:/Homeassistant/homeassistant/custom_components/netdata_docker
    python -m pytest tests/test_metrics_parser.py -v

Or without pytest:
    python -m unittest tests.test_metrics_parser -v
"""

import importlib.util
import json
import os
import sys
import unittest

# Load metrics_parser.py directly as a module file to avoid importing
# the package __init__.py (which requires Home Assistant dependencies).
_INTEGRATION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PARSER_PATH = os.path.join(_INTEGRATION_DIR, "metrics_parser.py")

spec = importlib.util.spec_from_file_location("metrics_parser", _PARSER_PATH)
metrics_parser = importlib.util.module_from_spec(spec)
sys.modules["metrics_parser"] = metrics_parser  # Required for dataclass processing
spec.loader.exec_module(metrics_parser)

ContainerMetrics = metrics_parser.ContainerMetrics
discover_containers = metrics_parser.discover_containers
_build_name_map = metrics_parser._build_name_map
_is_hex_id = metrics_parser._is_hex_id
_active_dimension = metrics_parser._active_dimension
_safe_dim_value = metrics_parser._safe_dim_value


# Path to the real allmetrics JSON snapshot
_COMPONENTS_DIR = os.path.dirname(_INTEGRATION_DIR)
_HOMEASSISTANT_DIR = os.path.dirname(_COMPONENTS_DIR)
_ALLMETRICS_PATH = os.path.join(
    _HOMEASSISTANT_DIR,
    "www", "tmp", "allmetric.json",
)


def _load_real_data() -> dict:
    """Load the real allmetric.json if available."""
    if not os.path.isfile(_ALLMETRICS_PATH):
        return {}
    with open(_ALLMETRICS_PATH, "r") as f:
        return json.load(f)


# ======================================================================
# Synthetic test data (simulates both docker_local and cgroup patterns)
# ======================================================================

SYNTHETIC_DATA_DOCKER_LOCAL = {
    # --- Container "nextcloud" via docker_local keys ---
    "docker_local.container_nextcloud_state": {
        "name": "docker_local.container_nextcloud_state",
        "family": "nextcloud",
        "context": "docker.container_state",
        "units": "state",
        "dimensions": {
            "running": {"name": "running", "value": 1.0},
            "paused": {"name": "paused", "value": 0.0},
            "stopped": {"name": "stopped", "value": 0.0},
            "created": {"name": "created", "value": 0.0},
            "restarting": {"name": "restarting", "value": 0.0},
        },
    },
    "docker_local.container_nextcloud_health_status": {
        "name": "docker_local.container_nextcloud_health_status",
        "family": "nextcloud",
        "context": "docker.container_health_status",
        "units": "status",
        "dimensions": {
            "healthy": {"name": "healthy", "value": 1.0},
            "unhealthy": {"name": "unhealthy", "value": 0.0},
            "not_running_unhealthy": {"name": "not_running_unhealthy", "value": 0.0},
        },
    },
    # --- Container "nextcloud" cgroup metrics (with friendly name) ---
    "cgroup_nextcloud.cpu": {
        "name": "cgroup_nextcloud.cpu",
        "family": "cpu",
        "context": "cgroup.cpu",
        "units": "percentage",
        "dimensions": {
            "user": {"name": "user", "value": 6.93},
            "system": {"name": "system", "value": 2.93},
        },
    },
    "cgroup_nextcloud.mem_usage": {
        "name": "cgroup_nextcloud.mem_usage",
        "family": "mem",
        "context": "cgroup.mem_usage",
        "units": "MiB",
        "dimensions": {
            "ram": {"name": "ram", "value": 273.11},
            "swap": {"name": "swap", "value": 0.0},
        },
    },
    "cgroup_nextcloud.mem_usage_limit": {
        "name": "cgroup_nextcloud.mem_usage_limit",
        "family": "mem",
        "context": "cgroup.mem_usage_limit",
        "units": "MiB",
        "dimensions": {
            "limit": {"name": "limit", "value": 8192.0},
        },
    },
    "cgroup_nextcloud.mem_utilization": {
        "name": "cgroup_nextcloud.mem_utilization",
        "family": "mem",
        "context": "cgroup.mem_utilization",
        "units": "percentage",
        "dimensions": {
            "utilization": {"name": "utilization", "value": 3.33},
        },
    },
    "cgroup_nextcloud.net_eth0": {
        "name": "cgroup_nextcloud.net_eth0",
        "family": "eth0",
        "context": "cgroup.net_net",
        "units": "kilobits/s",
        "dimensions": {
            "received": {"name": "received", "value": 12.5},
            "sent": {"name": "sent", "value": -5.3},
        },
    },
    "cgroup_nextcloud.pids_current": {
        "name": "cgroup_nextcloud.pids_current",
        "family": "pids",
        "context": "cgroup.pids_current",
        "units": "pids",
        "dimensions": {
            "pids": {"name": "pids", "value": 42.0},
        },
    },
    # --- Container "plex" via docker_local keys ---
    "docker_local.container_plex_state": {
        "name": "docker_local.container_plex_state",
        "family": "plex",
        "context": "docker.container_state",
        "units": "state",
        "dimensions": {
            "running": {"name": "running", "value": 0.0},
            "stopped": {"name": "stopped", "value": 1.0},
        },
    },
    "cgroup_plex.cpu": {
        "name": "cgroup_plex.cpu",
        "family": "cpu",
        "context": "cgroup.cpu",
        "units": "percentage",
        "dimensions": {
            "user": {"name": "user", "value": 0.0},
            "system": {"name": "system", "value": 0.0},
        },
    },
}

SYNTHETIC_DATA_HEX_ONLY = {
    # --- Container identified only by hex ID ---
    "cgroup_0434f3dc6d06.cpu": {
        "name": "cgroup_0434f3dc6d06.cpu",
        "family": "cpu",
        "context": "cgroup.cpu",
        "units": "percentage",
        "dimensions": {
            "user": {"name": "user", "value": 3.5},
            "system": {"name": "system", "value": 1.2},
        },
    },
    "cgroup_0434f3dc6d06.mem_usage": {
        "name": "cgroup_0434f3dc6d06.mem_usage",
        "family": "mem",
        "context": "cgroup.mem_usage",
        "units": "MiB",
        "dimensions": {
            "ram": {"name": "ram", "value": 150.75},
            "swap": {"name": "swap", "value": 0.0},
        },
    },
    "cgroup_0434f3dc6d06.net_eth0": {
        "name": "cgroup_0434f3dc6d06.net_eth0",
        "family": "eth0",
        "context": "cgroup.net_net",
        "units": "kilobits/s",
        "dimensions": {
            "received": {"name": "received", "value": 8.0},
            "sent": {"name": "sent", "value": -3.0},
        },
    },
}

SYNTHETIC_DATA_HEX_WITH_FRIENDLY_NAME = {
    # --- Hex ID key but name field has the friendly name ---
    "cgroup_abcdef123456.cpu": {
        "name": "cgroup_myapp.cpu",  # <-- Netdata renamed it!
        "family": "cpu",
        "context": "cgroup.cpu",
        "units": "percentage",
        "dimensions": {
            "user": {"name": "user", "value": 10.0},
            "system": {"name": "system", "value": 5.0},
        },
    },
    "cgroup_abcdef123456.mem_usage": {
        "name": "cgroup_myapp.mem_usage",
        "family": "mem",
        "context": "cgroup.mem_usage",
        "units": "MiB",
        "dimensions": {
            "ram": {"name": "ram", "value": 500.0},
        },
    },
}


# ======================================================================
# Tests
# ======================================================================


class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_is_hex_id_true(self):
        self.assertTrue(_is_hex_id("0434f3dc6d06"))
        self.assertTrue(_is_hex_id("abcdef123456"))
        self.assertTrue(_is_hex_id("0000000000000000"))

    def test_is_hex_id_false(self):
        self.assertFalse(_is_hex_id("nextcloud"))
        self.assertFalse(_is_hex_id("plex"))
        self.assertFalse(_is_hex_id("short"))
        self.assertFalse(_is_hex_id("0434f3DC6d06"))  # uppercase
        self.assertFalse(_is_hex_id(""))

    def test_safe_dim_value(self):
        dims = {"user": {"name": "user", "value": 6.93}}
        self.assertEqual(_safe_dim_value(dims, "user"), 6.93)
        self.assertEqual(_safe_dim_value(dims, "missing"), 0.0)
        self.assertEqual(_safe_dim_value(dims, "missing", default=-1.0), -1.0)
        self.assertEqual(_safe_dim_value({}, "anything"), 0.0)

    def test_active_dimension(self):
        dims = {
            "running": {"name": "running", "value": 1.0},
            "stopped": {"name": "stopped", "value": 0.0},
        }
        self.assertEqual(_active_dimension(dims), "running")

        dims2 = {
            "healthy": {"name": "healthy", "value": 0.0},
            "unhealthy": {"name": "unhealthy", "value": 1.0},
        }
        self.assertEqual(_active_dimension(dims2), "unhealthy")

    def test_active_dimension_none(self):
        dims = {
            "a": {"name": "a", "value": 0.0},
            "b": {"name": "b", "value": 0.0},
        }
        self.assertIsNone(_active_dimension(dims))


class TestNameResolution(unittest.TestCase):
    """Test the name mapping from hex IDs to friendly names."""

    def test_friendly_name_from_name_field(self):
        name_map = _build_name_map(SYNTHETIC_DATA_HEX_WITH_FRIENDLY_NAME)
        self.assertIn("abcdef123456", name_map)
        self.assertEqual(name_map["abcdef123456"], "myapp")

    def test_no_mapping_for_friendly_keys(self):
        name_map = _build_name_map(SYNTHETIC_DATA_DOCKER_LOCAL)
        # "nextcloud" is already a friendly name, so no mapping needed
        self.assertNotIn("nextcloud", name_map)

    def test_no_mapping_for_hex_echoing_itself(self):
        name_map = _build_name_map(SYNTHETIC_DATA_HEX_ONLY)
        # name field is "cgroup_0434f3dc6d06.cpu" which just echoes the hex
        self.assertNotIn("0434f3dc6d06", name_map)

    def test_empty_data(self):
        name_map = _build_name_map({})
        self.assertEqual(name_map, {})


class TestDiscoverDockerLocal(unittest.TestCase):
    """Test discovery from docker_local.container_* keys."""

    def setUp(self):
        self.containers = discover_containers(SYNTHETIC_DATA_DOCKER_LOCAL)

    def test_discovers_containers(self):
        self.assertIn("nextcloud", self.containers)
        self.assertIn("plex", self.containers)

    def test_nextcloud_state(self):
        cm = self.containers["nextcloud"]
        self.assertEqual(cm.state, "running")

    def test_nextcloud_health(self):
        cm = self.containers["nextcloud"]
        self.assertEqual(cm.health, "healthy")

    def test_nextcloud_cpu(self):
        cm = self.containers["nextcloud"]
        self.assertAlmostEqual(cm.cpu_percent, 9.86, places=2)

    def test_nextcloud_memory(self):
        cm = self.containers["nextcloud"]
        self.assertAlmostEqual(cm.memory_usage, 273.11, places=2)

    def test_nextcloud_memory_limit(self):
        cm = self.containers["nextcloud"]
        self.assertAlmostEqual(cm.memory_limit, 8192.0, places=1)

    def test_nextcloud_memory_utilization(self):
        cm = self.containers["nextcloud"]
        self.assertAlmostEqual(cm.memory_utilization, 3.33, places=2)

    def test_nextcloud_network(self):
        cm = self.containers["nextcloud"]
        self.assertAlmostEqual(cm.network_rx, 12.5, places=1)
        self.assertAlmostEqual(cm.network_tx, 5.3, places=1)

    def test_nextcloud_pids(self):
        cm = self.containers["nextcloud"]
        self.assertEqual(cm.pids, 42.0)

    def test_plex_state(self):
        cm = self.containers["plex"]
        self.assertEqual(cm.state, "stopped")

    def test_to_dict(self):
        cm = self.containers["nextcloud"]
        d = cm.to_dict()
        self.assertEqual(d["name"], "nextcloud")
        self.assertEqual(d["state"], "running")
        self.assertAlmostEqual(d["cpu_percent"], 9.86, places=2)


class TestDiscoverHexOnly(unittest.TestCase):
    """Test discovery when only hex-ID cgroup entries exist."""

    def setUp(self):
        self.containers = discover_containers(SYNTHETIC_DATA_HEX_ONLY)

    def test_discovers_by_hex_id(self):
        # Should fallback to the 12-char hex ID
        self.assertIn("0434f3dc6d06", self.containers)

    def test_cpu(self):
        cm = self.containers["0434f3dc6d06"]
        self.assertAlmostEqual(cm.cpu_percent, 4.7, places=1)

    def test_memory(self):
        cm = self.containers["0434f3dc6d06"]
        self.assertAlmostEqual(cm.memory_usage, 150.75, places=2)

    def test_network(self):
        cm = self.containers["0434f3dc6d06"]
        self.assertAlmostEqual(cm.network_rx, 8.0, places=1)
        self.assertAlmostEqual(cm.network_tx, 3.0, places=1)

    def test_container_id_stored(self):
        cm = self.containers["0434f3dc6d06"]
        self.assertEqual(cm.container_id, "0434f3dc6d06")


class TestDiscoverHexWithFriendlyName(unittest.TestCase):
    """Test name resolution when cgroup name field has a friendly name."""

    def setUp(self):
        self.containers = discover_containers(SYNTHETIC_DATA_HEX_WITH_FRIENDLY_NAME)

    def test_resolved_to_friendly_name(self):
        self.assertIn("myapp", self.containers)
        # Should NOT have the hex ID as a separate entry
        self.assertNotIn("abcdef123456", self.containers)

    def test_cpu(self):
        cm = self.containers["myapp"]
        self.assertAlmostEqual(cm.cpu_percent, 15.0, places=1)

    def test_memory(self):
        cm = self.containers["myapp"]
        self.assertAlmostEqual(cm.memory_usage, 500.0, places=1)

    def test_container_id_preserved(self):
        cm = self.containers["myapp"]
        self.assertEqual(cm.container_id, "abcdef123456")


class TestMixedData(unittest.TestCase):
    """Test discovery from mixed docker_local + cgroup data."""

    def setUp(self):
        combined = {}
        combined.update(SYNTHETIC_DATA_DOCKER_LOCAL)
        combined.update(SYNTHETIC_DATA_HEX_ONLY)
        combined.update(SYNTHETIC_DATA_HEX_WITH_FRIENDLY_NAME)
        self.containers = discover_containers(combined)

    def test_all_containers_found(self):
        self.assertIn("nextcloud", self.containers)
        self.assertIn("plex", self.containers)
        self.assertIn("0434f3dc6d06", self.containers)
        self.assertIn("myapp", self.containers)

    def test_no_duplicate_from_hex(self):
        self.assertNotIn("abcdef123456", self.containers)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_data(self):
        result = discover_containers({})
        self.assertEqual(result, {})

    def test_non_container_data(self):
        """System metrics should be ignored."""
        data = {
            "system.cpu": {
                "name": "system.cpu",
                "family": "cpu",
                "context": "system.cpu",
                "dimensions": {"user": {"name": "user", "value": 50.0}},
            },
            "net.eth0": {
                "name": "net.eth0",
                "family": "eth0",
                "context": "net.net",
                "dimensions": {
                    "received": {"name": "received", "value": 100.0},
                },
            },
        }
        result = discover_containers(data)
        self.assertEqual(result, {})

    def test_missing_dimensions(self):
        """Entries with missing or empty dimensions should be handled."""
        data = {
            "cgroup_aabbccddee11.cpu": {
                "name": "cgroup_aabbccddee11.cpu",
                "family": "cpu",
                "context": "cgroup.cpu",
                "dimensions": {},
            },
        }
        result = discover_containers(data)
        # CPU of 0 + memory of 0 + no state = filtered out
        self.assertEqual(result, {})

    def test_container_with_dashes(self):
        """Names with dashes like 'HA-OpenThread-Border-Router' should work."""
        data = {
            "docker_local.container_HA-OpenThread-Border-Router_state": {
                "name": "docker_local.container_HA-OpenThread-Border-Router_state",
                "family": "HA-OpenThread-Border-Router",
                "context": "docker.container_state",
                "dimensions": {
                    "running": {"name": "running", "value": 1.0},
                },
            },
            "cgroup_HA-OpenThread-Border-Router.cpu": {
                "name": "cgroup_HA-OpenThread-Border-Router.cpu",
                "family": "cpu",
                "context": "cgroup.cpu",
                "dimensions": {
                    "user": {"name": "user", "value": 1.2},
                    "system": {"name": "system", "value": 0.8},
                },
            },
        }
        result = discover_containers(data)
        self.assertIn("HA-OpenThread-Border-Router", result)
        cm = result["HA-OpenThread-Border-Router"]
        self.assertEqual(cm.state, "running")
        self.assertAlmostEqual(cm.cpu_percent, 2.0, places=1)


class TestRealData(unittest.TestCase):
    """Tests against the real allmetric.json snapshot."""

    @classmethod
    def setUpClass(cls):
        cls.data = _load_real_data()
        if cls.data:
            cls.containers = discover_containers(cls.data)
        else:
            cls.containers = {}

    @unittest.skipUnless(
        os.path.isfile(_ALLMETRICS_PATH),
        f"Real data file not found: {_ALLMETRICS_PATH}",
    )
    def test_discovers_containers(self):
        """Should discover multiple containers from real data."""
        self.assertGreater(len(self.containers), 0, "No containers discovered!")
        print(f"\n  [OK] Discovered {len(self.containers)} containers from real data")

    @unittest.skipUnless(
        os.path.isfile(_ALLMETRICS_PATH),
        f"Real data file not found: {_ALLMETRICS_PATH}",
    )
    def test_all_containers_have_cpu(self):
        """Every discovered container should have some CPU data."""
        for name, cm in self.containers.items():
            self.assertIsInstance(cm.cpu_percent, float, f"{name}: cpu not float")

    @unittest.skipUnless(
        os.path.isfile(_ALLMETRICS_PATH),
        f"Real data file not found: {_ALLMETRICS_PATH}",
    )
    def test_all_containers_have_memory(self):
        """Every discovered container should have memory data."""
        for name, cm in self.containers.items():
            self.assertIsInstance(cm.memory_usage, float, f"{name}: mem not float")

    @unittest.skipUnless(
        os.path.isfile(_ALLMETRICS_PATH),
        f"Real data file not found: {_ALLMETRICS_PATH}",
    )
    def test_print_summary(self):
        """Print a summary of discovered containers for manual review."""
        print(f"\n{'='*70}")
        print(f"  REAL DATA SUMMARY: {len(self.containers)} containers")
        print(f"{'='*70}")
        for name, cm in sorted(self.containers.items()):
            print(
                f"  {name:<35s} "
                f"state={cm.state:<10s} "
                f"cpu={cm.cpu_percent:>7.2f}% "
                f"mem={cm.memory_usage:>10.2f}MiB "
                f"rx={cm.network_rx:>8.2f} "
                f"tx={cm.network_tx:>8.2f}"
            )
        print(f"{'='*70}")
        # This "test" always passes; it's for human review
        self.assertTrue(True)

    @unittest.skipUnless(
        os.path.isfile(_ALLMETRICS_PATH),
        f"Real data file not found: {_ALLMETRICS_PATH}",
    )
    def test_no_system_metrics_leak(self):
        """System-level metrics (not containers) should not appear."""
        for name in self.containers:
            self.assertFalse(
                name.startswith("system."),
                f"System metric leaked as container: {name}",
            )
            self.assertFalse(
                name.startswith("net."),
                f"Net metric leaked as container: {name}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
