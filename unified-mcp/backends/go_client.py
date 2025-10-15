"""HTTP client for Go/whatsmeow bridge."""
from typing import Any

import requests

from constants import (
    DEFAULT_TIMEOUT,
    GO_BRIDGE_URL,
    HEALTH_CHECK_TIMEOUT,
    MEDIA_TIMEOUT,
    SHORT_TIMEOUT,
)


def send_message(recipient: str, message: str) -> tuple[bool, str]:
    """Send a text message via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/send_message",
            json={"recipient": recipient, "message": message},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending message: {e}"


def send_file(recipient: str, file_path: str) -> tuple[bool, str]:
    """Send a file via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/send_file",
            json={"recipient": recipient, "file_path": file_path},
            timeout=MEDIA_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending file: {e}"


def mark_as_read(chat_jid: str, message_ids: list[str], sender: str | None = None) -> tuple[bool, str, int, str]:
    """Mark messages as read via Go bridge.

    Phase 3: T011 - Fixed endpoint URL from /api/mark_as_read to /api/mark_read
    """
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/mark_read",  # Phase 3: T011 - Correct endpoint
            json={"chat_jid": chat_jid, "message_ids": message_ids, "sender": sender},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        # Phase 3: T012 - Return full response including count and error_code
        return data.get("success", False), data.get("message", ""), data.get("count", 0), data.get("error_code", "")
    except Exception as e:
        return False, f"Error marking as read: {e}", 0, "CONNECTION_ERROR"


def list_communities(query: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """List WhatsApp communities via Go bridge."""
    try:
        params = {"limit": limit}
        if query:
            params["query"] = query

        response = requests.get(
            f"{GO_BRIDGE_URL}/api/communities",
            params=params,
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("communities", [])
    except Exception as e:
        print(f"Error listing communities: {e}")
        return []


def get_community_groups(community_jid: str, limit: int = 100) -> list[dict[str, Any]]:
    """Get groups in a community via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/community/{community_jid}/groups",
            params={"limit": limit},
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("groups", [])
    except Exception as e:
        print(f"Error getting community groups: {e}")
        return []


def download_media(message_id: str, chat_jid: str) -> str | None:
    """Download media from a message via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/download_media",
            json={"message_id": message_id, "chat_jid": chat_jid},
            timeout=MEDIA_TIMEOUT
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
        response = requests.get(f"{GO_BRIDGE_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
        return response.status_code == 200
    except Exception:
        return False


def query_messages(
    chat_jid: str | None = None,
    sender: str | None = None,
    content: str | None = None,
    after_time: str | None = None,
    before_time: str | None = None,
    limit: int = 100,
    offset: int = 0,
    include_media: bool = False,
    media_type: str | None = None
) -> dict[str, Any]:
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
            timeout=DEFAULT_TIMEOUT
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


def get_message_stats() -> dict[str, Any]:
    """Get message statistics via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/stats",
            timeout=SHORT_TIMEOUT
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


# ============================================================================
# T043: Messaging MCP Tools - HTTP clients for Go bridge
# ============================================================================

def send_text_message(chat_jid: str, text: str) -> tuple[bool, str]:
    """Send text message via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/send-text",
            json={"chat_jid": chat_jid, "text": text},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending text message: {e}"


def send_media_message(chat_jid: str, media_path: str, media_type: str, caption: str | None = None) -> tuple[bool, str]:
    """Send media message via Go bridge."""
    try:
        payload = {
            "chat_jid": chat_jid,
            "media_path": media_path,
            "media_type": media_type
        }
        if caption:
            payload["caption"] = caption

        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/send-media",
            json=payload,
            timeout=MEDIA_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending media message: {e}"


def send_voice_note(chat_jid: str, audio_path: str) -> tuple[bool, str]:
    """Send voice note via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/send-voice",
            json={"chat_jid": chat_jid, "audio_path": audio_path},
            timeout=MEDIA_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending voice note: {e}"


def send_sticker(chat_jid: str, sticker_path: str) -> tuple[bool, str]:
    """Send sticker via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/send-sticker",
            json={"chat_jid": chat_jid, "sticker_path": sticker_path},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending sticker: {e}"


def send_contact(chat_jid: str, vcard: str) -> tuple[bool, str]:
    """Send contact vCard via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/send-contact",
            json={"chat_jid": chat_jid, "vcard": vcard},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending contact: {e}"


def send_location(chat_jid: str, latitude: float, longitude: float) -> tuple[bool, str]:
    """Send location via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/send-location",
            json={"chat_jid": chat_jid, "latitude": latitude, "longitude": longitude},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error sending location: {e}"


def react_to_message(chat_jid: str, message_id: str, emoji: str) -> tuple[bool, str]:
    """React to message via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/{message_id}/react",
            json={"chat_jid": chat_jid, "emoji": emoji},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error reacting to message: {e}"


def edit_message(message_id: str, new_text: str) -> tuple[bool, str]:
    """Edit message via Go bridge."""
    try:
        response = requests.put(
            f"{GO_BRIDGE_URL}/api/messages/{message_id}/edit",
            json={"new_text": new_text},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error editing message: {e}"


def delete_message(message_id: str) -> tuple[bool, str]:
    """Delete/revoke message via Go bridge."""
    try:
        response = requests.delete(
            f"{GO_BRIDGE_URL}/api/messages/{message_id}/revoke",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error deleting message: {e}"


def forward_message(message_id: str, to_chat_jid: str) -> tuple[bool, str]:
    """Forward message via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/messages/{message_id}/forward",
            json={"to_chat_jid": to_chat_jid},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error forwarding message: {e}"


def list_chats(limit: int = 20, archived: bool = False) -> list[dict[str, Any]]:
    """List chats via Go bridge."""
    try:
        params = {"limit": limit, "archived": "true" if archived else "false"}
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/chats/list",
            params=params,
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("chats", [])
    except Exception as e:
        print(f"Error listing chats: {e}")
        return []


def get_chat_metadata(chat_jid: str) -> dict[str, Any]:
    """Get chat metadata via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/chats/{chat_jid}",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting chat metadata: {e}")
        return {"success": False, "message": f"Error: {e}"}


# ============================================================================
# T044: Chat Management MCP Tools - HTTP clients for Go bridge
# ============================================================================

def archive_chat(chat_jid: str) -> tuple[bool, str]:
    """Archive a chat via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/chats/{chat_jid}/archive",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error archiving chat: {e}"


def unarchive_chat(chat_jid: str) -> tuple[bool, str]:
    """Unarchive a chat via Go bridge."""
    try:
        response = requests.delete(
            f"{GO_BRIDGE_URL}/api/chats/{chat_jid}/archive",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error unarchiving chat: {e}"


def pin_chat(chat_jid: str) -> tuple[bool, str]:
    """Pin a chat via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/chats/{chat_jid}/pin",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error pinning chat: {e}"


def unpin_chat(chat_jid: str) -> tuple[bool, str]:
    """Unpin a chat via Go bridge."""
    try:
        response = requests.delete(
            f"{GO_BRIDGE_URL}/api/chats/{chat_jid}/pin",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error unpinning chat: {e}"


def mute_chat(chat_jid: str, duration_seconds: int) -> tuple[bool, str]:
    """Mute a chat via Go bridge."""
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/chats/{chat_jid}/mute",
            json={"duration_seconds": duration_seconds},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error muting chat: {e}"


def unmute_chat(chat_jid: str) -> tuple[bool, str]:
    """Unmute a chat via Go bridge."""
    try:
        response = requests.delete(
            f"{GO_BRIDGE_URL}/api/chats/{chat_jid}/mute",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error unmuting chat: {e}"


# ============================================================================
# T045: Contact MCP Tools - HTTP clients for Go bridge
# ============================================================================

def search_contacts_v2(query: str) -> list[dict[str, Any]]:
    """Search contacts via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/contacts/search",
            params={"query": query},
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("contacts", [])
    except Exception as e:
        print(f"Error searching contacts: {e}")
        return []


def get_contact_details(jid: str) -> dict[str, Any]:
    """Get contact details via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/contacts/details",
            params={"jid": jid},
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting contact details: {e}")
        return {"success": False, "message": f"Error: {e}"}


def check_is_on_whatsapp(phone: str) -> dict[str, Any]:
    """Check if phone number is on WhatsApp via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/contacts/is-on-whatsapp",
            params={"phone": phone},
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error checking WhatsApp status: {e}")
        return {"success": False, "message": f"Error: {e}", "is_on_whatsapp": False}


def get_profile_picture(jid: str) -> dict[str, Any]:
    """Get profile picture URL via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/contacts/profile-picture",
            params={"jid": jid},
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting profile picture: {e}")
        return {"success": False, "message": f"Error: {e}"}


def update_profile_picture(image_path: str) -> tuple[bool, str]:
    """Update own profile picture via Go bridge."""
    try:
        response = requests.put(
            f"{GO_BRIDGE_URL}/api/profile/picture",
            json={"image_path": image_path},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error updating profile picture: {e}"


def get_contact_status(jid: str) -> dict[str, Any]:
    """Get contact status message via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/contacts/status",
            params={"jid": jid},
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting contact status: {e}")
        return {"success": False, "message": f"Error: {e}"}


def update_profile_status(status_text: str) -> tuple[bool, str]:
    """Update own status message via Go bridge."""
    try:
        response = requests.put(
            f"{GO_BRIDGE_URL}/api/profile/status",
            json={"status_text": status_text},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error updating status: {e}"


def get_linked_devices() -> dict[str, Any]:
    """Get linked WhatsApp devices via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/contacts/linked-devices",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting linked devices: {e}")
        return {"success": False, "message": f"Error: {e}", "devices": []}


# ============================================================================
# T049: Privacy MCP Tools - HTTP clients for Go bridge
# ============================================================================

def block_contact(jid: str | None = None, phone: str | None = None) -> tuple[bool, str]:
    """Block a contact via Go bridge."""
    try:
        payload = {}
        if jid:
            payload["jid"] = jid
        if phone:
            payload["phone"] = phone

        response = requests.post(
            f"{GO_BRIDGE_URL}/api/privacy/block",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error blocking contact: {e}"


def unblock_contact(jid: str | None = None, phone: str | None = None) -> tuple[bool, str]:
    """Unblock a contact via Go bridge."""
    try:
        payload = {}
        if jid:
            payload["jid"] = jid
        if phone:
            payload["phone"] = phone

        response = requests.post(
            f"{GO_BRIDGE_URL}/api/privacy/unblock",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error unblocking contact: {e}"


def get_blocked_contacts() -> dict[str, Any]:
    """Get list of blocked contacts via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/privacy/blocked",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting blocked contacts: {e}")
        return {"success": False, "message": f"Error: {e}", "blocked": [], "count": 0}


def get_privacy_settings() -> dict[str, Any]:
    """Get all privacy settings via Go bridge."""
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/privacy/settings",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting privacy settings: {e}")
        return {"success": False, "message": f"Error: {e}", "settings": {}}


def update_last_seen_privacy(value: str) -> tuple[bool, str]:
    """Update last seen privacy setting via Go bridge.

    Args:
        value: One of 'all', 'contacts', 'match_last_seen', 'none'
    """
    try:
        response = requests.put(
            f"{GO_BRIDGE_URL}/api/privacy/last-seen",
            json={"value": value},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error updating last seen privacy: {e}"


def update_profile_picture_privacy(value: str) -> tuple[bool, str]:
    """Update profile picture privacy setting via Go bridge.

    Args:
        value: One of 'all', 'contacts', 'match_last_seen', 'none'
    """
    try:
        response = requests.put(
            f"{GO_BRIDGE_URL}/api/privacy/profile-picture",
            json={"value": value},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error updating profile picture privacy: {e}"


def update_status_privacy(value: str) -> tuple[bool, str]:
    """Update status privacy setting via Go bridge.

    Args:
        value: One of 'all', 'contacts', 'match_last_seen', 'none'
    """
    try:
        response = requests.put(
            f"{GO_BRIDGE_URL}/api/privacy/status",
            json={"value": value},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error updating status privacy: {e}"


def update_online_privacy(value: str) -> tuple[bool, str]:
    """Update online privacy setting via Go bridge.

    Args:
        value: One of 'all', 'match_last_seen'
    """
    try:
        response = requests.put(
            f"{GO_BRIDGE_URL}/api/privacy/online",
            json={"value": value},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error updating online privacy: {e}"


# ============================================================================
# T053: Business MCP Tools - HTTP client for Go bridge
# ============================================================================

def get_business_profile(jid: str) -> dict[str, Any]:
    """Get business profile information via Go bridge.

    Args:
        jid: WhatsApp JID of the business account

    Returns:
        Dictionary with business profile details
    """
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/business/{jid}/profile",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting business profile: {e}")
        return {"success": False, "message": f"Error: {e}", "profile": None}


# ============================================================================
# T055: Newsletter MCP Tools - HTTP clients for Go bridge
# ============================================================================

def subscribe_to_newsletter(jid: str) -> tuple[bool, str]:
    """Subscribe to a newsletter via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/newsletters/{jid}/subscribe",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error subscribing to newsletter: {e}"


def unsubscribe_from_newsletter(jid: str) -> tuple[bool, str]:
    """Unsubscribe from a newsletter via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        response = requests.delete(
            f"{GO_BRIDGE_URL}/api/newsletters/{jid}/subscribe",
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error unsubscribing from newsletter: {e}"


def create_newsletter(name: str, description: str = "") -> dict[str, Any]:
    """Create a new newsletter via Go bridge.

    Args:
        name: Newsletter name
        description: Newsletter description (optional)

    Returns:
        Dictionary with creation result and newsletter JID
    """
    try:
        payload = {"name": name}
        if description:
            payload["description"] = description

        response = requests.post(
            f"{GO_BRIDGE_URL}/api/newsletters/create",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error creating newsletter: {e}")
        return {"success": False, "message": f"Error: {e}", "jid": None}


def get_newsletter_metadata(jid: str) -> dict[str, Any]:
    """Get newsletter metadata via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter

    Returns:
        Dictionary with newsletter metadata
    """
    try:
        response = requests.get(
            f"{GO_BRIDGE_URL}/api/newsletters/{jid}",
            timeout=SHORT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting newsletter metadata: {e}")
        return {"success": False, "message": f"Error: {e}", "newsletter": None}


def react_to_newsletter_message(jid: str, message_id: str, emoji: str) -> tuple[bool, str]:
    """React to a newsletter message via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter
        message_id: ID of the message to react to
        emoji: Emoji to react with

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        response = requests.post(
            f"{GO_BRIDGE_URL}/api/newsletters/{jid}/messages/{message_id}/react",
            json={"emoji": emoji},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        return data.get("success", False), data.get("message", "")
    except Exception as e:
        return False, f"Error reacting to newsletter message: {e}"
