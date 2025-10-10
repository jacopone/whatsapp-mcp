"""
HTTP client for Go/whatsmeow bridge.
"""
import requests
from typing import List, Dict, Any, Optional, Tuple

GO_BRIDGE_URL = "http://localhost:8080"


def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    """Send a text message via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/send_message",
            json={"recipient": recipient, "message": message},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending message: {e}"


def send_file(recipient: str, file_path: str) -> Tuple[bool, str]:
    """Send a file via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/send_file",
            json={"recipient": recipient, "file_path": file_path},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending file: {e}"


def mark_as_read(chat_jid: str, message_ids: List[str], sender: Optional[str] = None) -> Tuple[bool, str]:
    """Mark messages as read via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/mark_as_read",
            json={"chat_jid": chat_jid, "message_ids": message_ids, "sender": sender},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error marking as read: {e}"


def list_communities(query: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """List WhatsApp communities via Go bridge."""
    try:
        params = {"limit": limit}
        if query:
            params["query"] = query

        response = requests.get(
            f"{GO_BRIDGE_URL}/api/communities",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("communities", [])
    except Exception as e:
        print(f"Error listing communities: {e}")
        return []


def get_community_groups(community_jid: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get groups in a community via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/community/{community_jid}/groups",
            params={"limit": limit},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("groups", [])
    except Exception as e:
        print(f"Error getting community groups: {e}")
        return []


def download_media(message_id: str, chat_jid: str) -> Optional[str]:
    """Download media from a message via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/download_media",
            json={"message_id": message_id, "chat_jid": chat_jid},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            return data.get("file_path")
        return None
    except Exception as e:
        print(f"Error downloading media: {e}")
        return None


def health_check() -> bool:
    """Check if Go bridge is healthy."""
    try:
        response = requests.get(f"{GO_BRIDGE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def query_messages(
    chat_jid: Optional[str] = None,
    sender: Optional[str] = None,
    content: Optional[str] = None,
    after_time: Optional[str] = None,
    before_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    include_media: bool = False,
    media_type: Optional[str] = None
) -> Dict[str, Any]:
    """Query messages with various filters via Go bridge."""
    try:
        params = {
            "limit": limit,
            "offset": offset,
            "include_media": "true" if include_media else "false"
        }

        if chat_jid:
            params["chat_jid"] = chat_jid
        if sender:
            params["sender"] = sender
        if content:
            params["content"] = content
        if after_time:
            params["after_time"] = after_time
        if before_time:
            params["before_time"] = before_time
        if media_type:
            params["media_type"] = media_type

        response = requests.get(
            f"{GO_BRIDGE_URL}/api/messages",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error querying messages: {e}")
        return {
            "success": False,
            "message": f"Error querying messages: {e}",
            "messages": [],
            "total": 0
        }


def get_message_stats() -> Dict[str, Any]:
    """Get message statistics via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/stats",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting message stats: {e}")
        return {
            "success": False,
            "total_messages": 0,
            "total_chats": 0,
            "total_contacts": 0
        }
