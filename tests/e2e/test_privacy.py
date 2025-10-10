#!/usr/bin/env python3
"""
Integration Test: T050 - Privacy Operations

Tests all privacy features across Go and Baileys bridges:
- Blocking/unblocking contacts
- Privacy settings (last seen, profile, status, online)
- Read receipts privacy (Baileys-only)

Acceptance Criteria:
- All privacy operations work
- Settings persist across operations
- Routing to correct backend
"""

import sys
import os
import time
import requests
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../unified-mcp'))

# Test configuration
GO_BRIDGE_URL = "http://localhost:8080"
BAILEYS_BRIDGE_URL = "http://localhost:8081"
TEST_JID = "1234567890@s.whatsapp.net"  # Replace with actual test JID
TEST_PHONE = "1234567890"  # Replace with actual test phone

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class PrivacyIntegrationTest:
    """Integration test suite for privacy operations"""

    def __init__(self):
        self.test_results = []
        self.go_bridge_available = False
        self.baileys_bridge_available = False

    def log_test(self, name: str, passed: bool, message: str = ""):
        """Log test result with color"""
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"{status} | {name}")
        if message:
            print(f"      {message}")
        self.test_results.append((name, passed, message))

    def check_backend_health(self) -> bool:
        """Check if both backends are available"""
        print(f"\n{BLUE}=== Checking Backend Health ==={RESET}")

        # Check Go bridge
        try:
            response = requests.get(f"{GO_BRIDGE_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.go_bridge_available = data.get("whatsapp_connected", False)
                self.log_test(
                    "Go Bridge Health",
                    self.go_bridge_available,
                    f"Status: {data.get('status')}, Connected: {data.get('whatsapp_connected')}"
                )
            else:
                self.log_test("Go Bridge Health", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Go Bridge Health", False, str(e))

        # Check Baileys bridge
        try:
            response = requests.get(f"{BAILEYS_BRIDGE_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.baileys_bridge_available = data.get("connected", False)
                self.log_test(
                    "Baileys Bridge Health",
                    self.baileys_bridge_available,
                    f"Status: {data.get('status')}, Connected: {data.get('connected')}"
                )
            else:
                self.log_test("Baileys Bridge Health", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Baileys Bridge Health", False, str(e))

        return self.go_bridge_available or self.baileys_bridge_available

    def test_block_contact(self) -> bool:
        """Test blocking a contact via Go bridge"""
        print(f"\n{BLUE}=== Testing Block Contact ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Block Contact", False, "Go bridge not available")
            return False

        try:
            response = requests.post(
                f"{GO_BRIDGE_URL}/api/privacy/block",
                json={"jid": TEST_JID},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "Block Contact",
                    success,
                    f"Response: {data.get('message')}, JID: {data.get('jid')}"
                )
                return success
            else:
                self.log_test("Block Contact", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Block Contact", False, str(e))
            return False

    def test_get_blocked_contacts(self) -> bool:
        """Test getting list of blocked contacts"""
        print(f"\n{BLUE}=== Testing Get Blocked Contacts ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Get Blocked Contacts", False, "Go bridge not available")
            return False

        try:
            response = requests.get(
                f"{GO_BRIDGE_URL}/api/privacy/blocked",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                count = data.get("count", 0)
                self.log_test(
                    "Get Blocked Contacts",
                    success,
                    f"Count: {count} blocked contacts"
                )
                return success
            else:
                self.log_test("Get Blocked Contacts", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Blocked Contacts", False, str(e))
            return False

    def test_unblock_contact(self) -> bool:
        """Test unblocking a contact via Go bridge"""
        print(f"\n{BLUE}=== Testing Unblock Contact ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Unblock Contact", False, "Go bridge not available")
            return False

        try:
            response = requests.post(
                f"{GO_BRIDGE_URL}/api/privacy/unblock",
                json={"jid": TEST_JID},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "Unblock Contact",
                    success,
                    f"Response: {data.get('message')}, JID: {data.get('jid')}"
                )
                return success
            else:
                self.log_test("Unblock Contact", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Unblock Contact", False, str(e))
            return False

    def test_get_privacy_settings(self) -> Dict[str, Any]:
        """Test getting all privacy settings"""
        print(f"\n{BLUE}=== Testing Get Privacy Settings ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Get Privacy Settings", False, "Go bridge not available")
            return {}

        try:
            response = requests.get(
                f"{GO_BRIDGE_URL}/api/privacy/settings",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                settings = data.get("settings", {})
                self.log_test(
                    "Get Privacy Settings",
                    success,
                    f"Settings: {list(settings.keys())}"
                )
                return settings
            else:
                self.log_test("Get Privacy Settings", False, f"HTTP {response.status_code}")
                return {}
        except Exception as e:
            self.log_test("Get Privacy Settings", False, str(e))
            return {}

    def test_update_last_seen_privacy(self, value: str = "contacts") -> bool:
        """Test updating last seen privacy setting"""
        print(f"\n{BLUE}=== Testing Update Last Seen Privacy ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Update Last Seen Privacy", False, "Go bridge not available")
            return False

        try:
            response = requests.put(
                f"{GO_BRIDGE_URL}/api/privacy/last-seen",
                json={"value": value},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "Update Last Seen Privacy",
                    success,
                    f"Value: {value}, Response: {data.get('message')}"
                )
                return success
            else:
                self.log_test("Update Last Seen Privacy", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Update Last Seen Privacy", False, str(e))
            return False

    def test_update_profile_picture_privacy(self, value: str = "contacts") -> bool:
        """Test updating profile picture privacy setting"""
        print(f"\n{BLUE}=== Testing Update Profile Picture Privacy ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Update Profile Picture Privacy", False, "Go bridge not available")
            return False

        try:
            response = requests.put(
                f"{GO_BRIDGE_URL}/api/privacy/profile-picture",
                json={"value": value},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "Update Profile Picture Privacy",
                    success,
                    f"Value: {value}, Response: {data.get('message')}"
                )
                return success
            else:
                self.log_test("Update Profile Picture Privacy", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Update Profile Picture Privacy", False, str(e))
            return False

    def test_update_status_privacy(self, value: str = "contacts") -> bool:
        """Test updating status privacy setting"""
        print(f"\n{BLUE}=== Testing Update Status Privacy ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Update Status Privacy", False, "Go bridge not available")
            return False

        try:
            response = requests.put(
                f"{GO_BRIDGE_URL}/api/privacy/status",
                json={"value": value},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "Update Status Privacy",
                    success,
                    f"Value: {value}, Response: {data.get('message')}"
                )
                return success
            else:
                self.log_test("Update Status Privacy", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Update Status Privacy", False, str(e))
            return False

    def test_update_online_privacy(self, value: str = "all") -> bool:
        """Test updating online status privacy setting"""
        print(f"\n{BLUE}=== Testing Update Online Privacy ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Update Online Privacy", False, "Go bridge not available")
            return False

        try:
            response = requests.put(
                f"{GO_BRIDGE_URL}/api/privacy/online",
                json={"value": value},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "Update Online Privacy",
                    success,
                    f"Value: {value}, Response: {data.get('message')}"
                )
                return success
            else:
                self.log_test("Update Online Privacy", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Update Online Privacy", False, str(e))
            return False

    def test_get_read_receipts_privacy(self) -> bool:
        """Test getting read receipts privacy setting (Baileys)"""
        print(f"\n{BLUE}=== Testing Get Read Receipts Privacy ==={RESET}")

        if not self.baileys_bridge_available:
            self.log_test("Get Read Receipts Privacy", False, "Baileys bridge not available")
            return False

        try:
            response = requests.get(
                f"{BAILEYS_BRIDGE_URL}/api/privacy/read-receipts",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                enabled = data.get("enabled", False)
                self.log_test(
                    "Get Read Receipts Privacy",
                    success,
                    f"Enabled: {enabled}"
                )
                return success
            else:
                self.log_test("Get Read Receipts Privacy", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Get Read Receipts Privacy", False, str(e))
            return False

    def test_update_read_receipts_privacy(self, enabled: bool = False) -> bool:
        """Test updating read receipts privacy setting (Baileys)"""
        print(f"\n{BLUE}=== Testing Update Read Receipts Privacy ==={RESET}")

        if not self.baileys_bridge_available:
            self.log_test("Update Read Receipts Privacy", False, "Baileys bridge not available")
            return False

        try:
            response = requests.put(
                f"{BAILEYS_BRIDGE_URL}/api/privacy/read-receipts",
                json={"enabled": enabled},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                self.log_test(
                    "Update Read Receipts Privacy",
                    success,
                    f"Enabled: {enabled}, Response: {data.get('message')}"
                )
                return success
            else:
                self.log_test("Update Read Receipts Privacy", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Update Read Receipts Privacy", False, str(e))
            return False

    def test_privacy_settings_persistence(self) -> bool:
        """Test that privacy settings persist after update"""
        print(f"\n{BLUE}=== Testing Privacy Settings Persistence ==={RESET}")

        if not self.go_bridge_available:
            self.log_test("Privacy Settings Persistence", False, "Go bridge not available")
            return False

        try:
            # Get current settings
            settings_before = self.test_get_privacy_settings()

            # Wait a moment
            time.sleep(1)

            # Get settings again
            settings_after = self.test_get_privacy_settings()

            # Compare
            persisted = settings_before == settings_after and len(settings_before) > 0
            self.log_test(
                "Privacy Settings Persistence",
                persisted,
                f"Settings consistent: {persisted}"
            )
            return persisted
        except Exception as e:
            self.log_test("Privacy Settings Persistence", False, str(e))
            return False

    def run_all_tests(self) -> bool:
        """Run all integration tests"""
        print(f"\n{YELLOW}╔═══════════════════════════════════════════════════════╗{RESET}")
        print(f"{YELLOW}║   T050: Privacy Operations Integration Test          ║{RESET}")
        print(f"{YELLOW}╚═══════════════════════════════════════════════════════╝{RESET}")

        # Check backends first
        if not self.check_backend_health():
            print(f"\n{RED}ERROR: No backends available. Cannot run tests.{RESET}")
            print(f"{YELLOW}NOTE: This is expected if WhatsApp is not connected.{RESET}")
            print(f"{YELLOW}      The test framework is working correctly.{RESET}")
            return False

        # Run blocking tests
        if self.go_bridge_available:
            self.test_block_contact()
            time.sleep(1)
            self.test_get_blocked_contacts()
            time.sleep(1)
            self.test_unblock_contact()
            time.sleep(1)

        # Run privacy settings tests
        if self.go_bridge_available:
            self.test_get_privacy_settings()
            time.sleep(1)
            self.test_update_last_seen_privacy("contacts")
            time.sleep(1)
            self.test_update_profile_picture_privacy("contacts")
            time.sleep(1)
            self.test_update_status_privacy("contacts")
            time.sleep(1)
            self.test_update_online_privacy("all")
            time.sleep(1)
            self.test_privacy_settings_persistence()

        # Run read receipts tests (Baileys)
        if self.baileys_bridge_available:
            self.test_get_read_receipts_privacy()
            time.sleep(1)
            self.test_update_read_receipts_privacy(False)
            time.sleep(1)
            self.test_update_read_receipts_privacy(True)

        # Print summary
        print(f"\n{YELLOW}╔═══════════════════════════════════════════════════════╗{RESET}")
        print(f"{YELLOW}║   Test Summary                                        ║{RESET}")
        print(f"{YELLOW}╚═══════════════════════════════════════════════════════╝{RESET}")

        passed = sum(1 for _, p, _ in self.test_results if p)
        total = len(self.test_results)
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}")
        print(f"Success Rate: {(passed/total*100):.1f}%")

        if failed > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for name, passed_test, message in self.test_results:
                if not passed_test:
                    print(f"  - {name}: {message}")

        return failed == 0


def main():
    """Main entry point"""
    test = PrivacyIntegrationTest()
    success = test.run_all_tests()

    print(f"\n{YELLOW}═══════════════════════════════════════════════════════{RESET}")
    if success:
        print(f"{GREEN}✓ T050 INTEGRATION TEST PASSED{RESET}")
        print(f"{GREEN}  All privacy operations work correctly{RESET}")
        sys.exit(0)
    else:
        print(f"{YELLOW}⚠ T050 INTEGRATION TEST COMPLETED WITH ISSUES{RESET}")
        print(f"{YELLOW}  Review failed tests above{RESET}")
        print(f"{YELLOW}  Note: Some failures expected without WhatsApp connection{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
