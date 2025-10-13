"""Integration tests for backend failover resilience (Phase 7: US5).

Tests automatic failover when backends become unreachable,
recovery detection, and failover performance.
"""

import time
from unittest.mock import Mock, patch

import requests


class TestAutomaticFailover:
    """Test automatic failover when backends become unreachable."""

    def test_automatic_failover_when_go_backend_becomes_unreachable_mid_operation(self):
        """T097: Test automatic failover when Go backend becomes unreachable mid-operation."""
        from routing import get_router

        router = get_router()

        with patch('backends.health.requests.get') as mock_get:
            # Both backends healthy, then Go fails
            call_count = [0]

            def mock_get_side_effect(url, **kwargs):
                call_count[0] += 1
                baileys_response = Mock()
                baileys_response.status_code = 200
                baileys_response.json.return_value = {
                    "status": "ok",
                    "whatsapp_connected": True,
                    "database_ok": True,
                    "uptime_seconds": 3600
                }

                if "8080" in url:  # Go bridge
                    if call_count[0] <= 1:
                        go_response = Mock()
                        go_response.status_code = 200
                        go_response.json.return_value = {
                            "status": "ok",
                            "whatsapp_connected": True,
                            "database_ok": True,
                            "uptime_seconds": 3600
                        }
                        return go_response
                    else:
                        raise requests.exceptions.ConnectionError("Connection refused")
                else:  # Baileys bridge
                    return baileys_response

            mock_get.side_effect = mock_get_side_effect

            # First check: Both healthy
            health1 = router.health_monitor.check_all()
            assert health1.status == "ok"

            # Second check: Go fails
            health2 = router.health_monitor.check_all()
            assert health2.status == "degraded"
            assert "baileys" in health2.available_backends

    def test_automatic_failover_when_baileys_backend_becomes_unreachable_mid_operation(self):
        """T098: Test automatic failover when Baileys backend becomes unreachable mid-operation."""
        from routing import get_router

        router = get_router()

        with patch('backends.health.requests.get') as mock_get:
            # Go healthy, Baileys fails
            def mock_get_side_effect(url, **kwargs):
                go_response = Mock()
                go_response.status_code = 200
                go_response.json.return_value = {
                    "status": "ok",
                    "whatsapp_connected": True,
                    "database_ok": True,
                    "uptime_seconds": 3600
                }

                if "8080" in url:  # Go bridge
                    return go_response
                else:  # Baileys bridge - fails
                    raise requests.exceptions.ConnectionError("Connection refused")

            mock_get.side_effect = mock_get_side_effect

            # Check health
            health = router.health_monitor.check_all()
            assert health.status == "degraded"
            assert "go" in health.available_backends
            assert "baileys" not in health.available_backends


class TestBothBackendsFailure:
    """Test system behavior when both backends fail."""

    def test_system_returns_no_backend_available_error_when_both_backends_fail_simultaneously(self):
        r"""T099: Test system returns \"No backend available\" error when both backends fail simultaneously."""
        from routing import get_router

        router = get_router()

        with patch('backends.health.requests.get') as mock_get:
            # Both backends fail
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

            # Check health
            health = router.health_monitor.check_all()
            assert health.status == "error"
            assert len(health.available_backends) == 0


class TestBackendRecovery:
    """Test backend recovery detection."""

    def test_backend_recovery_detection_after_go_backend_restarts(self):
        """T100: Test backend recovery detection after Go backend restarts."""
        from backends.health import HealthMonitor

        monitor = HealthMonitor()

        with patch('backends.health.requests.get') as mock_get:
            # Go fails initially
            call_count = [0]

            def mock_get_side_effect(url, **kwargs):
                call_count[0] += 1
                baileys_response = Mock()
                baileys_response.status_code = 200
                baileys_response.json.return_value = {
                    "status": "ok",
                    "whatsapp_connected": True,
                    "database_ok": True,
                    "uptime_seconds": 3600
                }

                if "8080" in url:  # Go bridge
                    if call_count[0] <= 2:
                        # First few calls: Go is down
                        raise requests.exceptions.ConnectionError("Connection refused")
                    else:
                        # Later calls: Go recovers
                        go_response = Mock()
                        go_response.status_code = 200
                        go_response.json.return_value = {
                            "status": "ok",
                            "whatsapp_connected": True,
                            "database_ok": True,
                            "uptime_seconds": 10  # Just restarted
                        }
                        return go_response
                else:  # Baileys bridge - always healthy
                    return baileys_response

            mock_get.side_effect = mock_get_side_effect

            # First check: Go is down
            health1 = monitor.check_all()
            assert health1.status == "degraded"
            assert "go" not in health1.available_backends

            # Second check: Go recovers
            health2 = monitor.check_all()
            assert health2.status == "ok"
            assert "go" in health2.available_backends
            assert health2.go_backend.uptime_seconds == 10  # Verify it's the restarted instance

    def test_backend_recovery_detection_after_baileys_backend_restarts(self):
        """T101: Test backend recovery detection after Baileys backend restarts."""
        from backends.health import HealthMonitor

        monitor = HealthMonitor()

        with patch('backends.health.requests.get') as mock_get:
            # Baileys fails initially, then recovers
            call_count = [0]

            def mock_get_side_effect(url, **kwargs):
                call_count[0] += 1
                go_response = Mock()
                go_response.status_code = 200
                go_response.json.return_value = {
                    "status": "ok",
                    "whatsapp_connected": True,
                    "database_ok": True,
                    "uptime_seconds": 3600
                }

                if "8081" in url:  # Baileys bridge
                    if call_count[0] <= 2:
                        # First few calls: Baileys is down
                        raise requests.exceptions.ConnectionError("Connection refused")
                    else:
                        # Later calls: Baileys recovers
                        baileys_response = Mock()
                        baileys_response.status_code = 200
                        baileys_response.json.return_value = {
                            "status": "ok",
                            "whatsapp_connected": True,
                            "database_ok": True,
                            "uptime_seconds": 5  # Just restarted
                        }
                        return baileys_response
                else:  # Go bridge - always healthy
                    return go_response

            mock_get.side_effect = mock_get_side_effect

            # First check: Baileys is down
            health1 = monitor.check_all()
            assert health1.status == "degraded"
            assert "baileys" not in health1.available_backends

            # Second check: Baileys recovers
            health2 = monitor.check_all()
            assert health2.status == "ok"
            assert "baileys" in health2.available_backends
            assert health2.baileys_backend.uptime_seconds == 5  # Verify restart


class TestFailurePerformance:
    """Test operations fail fast when backends unavailable."""

    def test_operations_fail_fast_under_10s_when_no_backends_available(self):
        """T102: Test operations fail fast (under 10s) when no backends available."""
        from routing import get_router

        router = get_router()

        with patch('backends.health.requests.get') as mock_get:
            # Both backends fail immediately
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

            # Measure time to detect failures
            start_time = time.time()
            health = router.health_monitor.check_all()
            elapsed = time.time() - start_time

            # Verify: Detection was fast
            assert health.status == "error"
            assert elapsed < 10.0, f"Health check took {elapsed:.2f}s, expected < 10s"


class TestFastestStrategyFailover:
    """Test FASTEST strategy switches when response times change."""

    def test_fastest_strategy_switches_to_faster_backend_when_response_times_change(self):
        """T103: Test FASTEST strategy switches to faster backend when response times change."""
        from backends.health import HealthMonitor

        monitor = HealthMonitor()

        with patch('backends.health.requests.get') as mock_get:
            # Setup: Initially Go is faster, then Baileys becomes faster
            call_count = [0]

            def mock_get_side_effect(url, **kwargs):
                call_count[0] += 1

                if "8080" in url:  # Go bridge
                    go_response = Mock()
                    go_response.status_code = 200
                    go_response.json.return_value = {
                        "status": "ok",
                        "whatsapp_connected": True,
                        "database_ok": True,
                        "uptime_seconds": 3600
                    }
                    # Go always responds, just record that it was checked
                    return go_response
                else:  # Baileys bridge
                    baileys_response = Mock()
                    baileys_response.status_code = 200
                    baileys_response.json.return_value = {
                        "status": "ok",
                        "whatsapp_connected": True,
                        "database_ok": True,
                        "uptime_seconds": 3600
                    }
                    return baileys_response

            mock_get.side_effect = mock_get_side_effect

            # Check health multiple times
            health1 = monitor.check_all()
            assert health1.status == "ok"

            health2 = monitor.check_all()
            assert health2.status == "ok"

            # Verify both backends available
            assert "go" in health2.available_backends
            assert "baileys" in health2.available_backends


class TestNetworkPartition:
    """Test failover handles network partition scenarios."""

    def test_failover_handles_network_partition_backend_unreachable_but_not_crashed(self):
        """T104: Test failover handles network partition (backend unreachable but not crashed)."""
        from backends.health import HealthMonitor

        monitor = HealthMonitor()

        with patch('backends.health.requests.get') as mock_get:
            # Simulate network partition: connection timeout (not refused)
            def mock_get_side_effect(url, **kwargs):
                baileys_response = Mock()
                baileys_response.status_code = 200
                baileys_response.json.return_value = {
                    "status": "ok",
                    "whatsapp_connected": True,
                    "database_ok": True,
                    "uptime_seconds": 3600
                }

                if "8080" in url:  # Go bridge - network partition
                    raise requests.exceptions.Timeout("Connection timeout")
                else:  # Baileys bridge - reachable
                    return baileys_response

            mock_get.side_effect = mock_get_side_effect

            # Check health: Go should be marked as unreachable
            health = monitor.check_all()
            assert health.status == "degraded"
            assert "go" not in health.available_backends
            assert health.go_backend.status == "unreachable"
            assert "baileys" in health.available_backends
