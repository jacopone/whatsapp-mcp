"""
HTTP client for Baileys bridge.
"""
import requests
from typing import Dict, List, Any
import time

from constants import (
    BAILEYS_BRIDGE_URL,
    HEALTH_CHECK_TIMEOUT,
    SHORT_TIMEOUT
)


def get_sync_status() -> Dict[str, Any]:
    """Get current history sync status."""
    try:
        response = requests.get(f"{BAILEYS_BRIDGE_URL}/api/sync/status", timeout=HEALTH_CHECK_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "connected": False,
            "is_syncing": False,
            "error": str(e)
        }


def wait_for_sync_completion(timeout: int = 300, poll_interval: int = 5) -> bool:
    """
    Wait for history sync to complete.

    Args:
        timeout: Maximum time to wait in seconds (default 5 minutes)
        poll_interval: Time between status checks in seconds

    Returns:
        True if sync completed successfully, False if timeout or error
    """
    start_time = time.time()

    print("⏳ Waiting for Baileys history sync to complete...")

    while time.time() - start_time < timeout:
        status = get_sync_status()

        if not status.get("connected"):
            print("❌ Baileys bridge not connected")
            return False

        is_syncing = status.get("is_syncing", False)
        is_latest = status.get("is_latest", False)
        progress = status.get("progress_percent", 0)
        messages_synced = status.get("messages_synced", 0)

        print(f"📊 Progress: {progress}%, Messages: {messages_synced}, Syncing: {is_syncing}")

        if is_latest and not is_syncing:
            print("✅ History sync complete!")
            return True

        time.sleep(poll_interval)

    print("⏰ Timeout waiting for sync to complete")
    return False


def get_messages() -> List[Dict[str, Any]]:
    """Fetch all synced messages from Baileys."""
    try:
        response = requests.get(f"{BAILEYS_BRIDGE_URL}/api/messages", timeout=SHORT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("messages", [])
    except Exception as e:
        print(f"Error fetching messages from Baileys: {e}")
        return []


def clear_temp_data() -> bool:
    """Clear Baileys temporary data after successful sync."""
    try:
        response = requests.post(f"{BAILEYS_BRIDGE_URL}/api/clear", timeout=HEALTH_CHECK_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data.get("success", False)
    except Exception as e:
        print(f"Error clearing Baileys data: {e}")
        return False


def health_check() -> bool:
    """Check if Baileys bridge is healthy."""
    try:
        response = requests.get(f"{BAILEYS_BRIDGE_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
        return response.status_code == 200
    except Exception:
        return False


# ============================================================================
# T053: Business MCP Tools - HTTP clients for Baileys bridge
# ============================================================================

def get_business_catalog(jid: str) -> Dict[str, Any]:
    """Get business catalog via Baileys bridge.

    Args:
        jid: WhatsApp JID of the business account

    Returns:
        Dictionary with catalog information
    """
    try:
        response = requests.get(
            f"{BAILEYS_BRIDGE_URL}/api/business/{jid}/catalog",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting business catalog: {e}")
        return {"success": False, "message": f"Error: {e}", "catalog": None, "product_count": 0}


def get_product_details(jid: str, product_id: str) -> Dict[str, Any]:
    """Get product details from business catalog via Baileys bridge.

    Args:
        jid: WhatsApp JID of the business account
        product_id: Product ID to retrieve

    Returns:
        Dictionary with product details
    """
    try:
        response = requests.get(
            f"{BAILEYS_BRIDGE_URL}/api/business/{jid}/catalog/{product_id}",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting product details: {e}")
        return {"success": False, "message": f"Error: {e}", "product": None}
