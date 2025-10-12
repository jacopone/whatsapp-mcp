"""
Unified WhatsApp MCP Server

Combines Go/whatsmeow and Baileys bridges for maximum functionality:
- Go: Communities, mark as read, media operations
- Baileys: History sync
- Hybrid: Smart combination of both
"""
import sys
sys.path.insert(0, '../whatsapp-mcp-server')

from typing import List, Dict, Any, Optional, Tuple
from mcp.server.fastmcp import FastMCP
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media,
    mark_as_read as whatsapp_mark_as_read,
    list_communities as whatsapp_list_communities,
    get_community_groups as whatsapp_get_community_groups,
    mark_community_as_read as whatsapp_mark_community_as_read
)
from backends import go_client, baileys_client
from sync import sync_baileys_to_go, sync_all_chats
import backends.go_client as go

# Initialize FastMCP server
mcp = FastMCP("whatsapp-unified")

# ============================================================================
# BACKEND STATUS & HEALTH CHECKS
# ============================================================================

@mcp.tool()
def backend_status() -> Dict[str, Any]:
    """Check health status of both Go and Baileys backends."""
    go_healthy = go_client.health_check()
    baileys_healthy = baileys_client.health_check()
    baileys_status = baileys_client.get_sync_status()

    return {
        "go_bridge": {
            "healthy": go_healthy,
            "url": go_client.GO_BRIDGE_URL
        },
        "baileys_bridge": {
            "healthy": baileys_healthy,
            "url": baileys_client.BAILEYS_BRIDGE_URL,
            "connected": baileys_status.get("connected", False),
            "syncing": baileys_status.get("is_syncing", False),
            "messages_synced": baileys_status.get("messages_synced", 0),
            "progress_percent": baileys_status.get("progress_percent", 0)
        },
        "overall_status": "healthy" if (go_healthy and baileys_healthy) else "degraded"
    }

# ============================================================================
# PASS-THROUGH TOOLS (All existing functionality via Go)
# ============================================================================

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number."""
    return whatsapp_search_contacts(query)

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context."""
    return whatsapp_list_messages(
        after, before, sender_phone_number, chat_jid, query,
        limit, page, include_context, context_before, context_after
    )

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria."""
    return whatsapp_list_chats(query, limit, page, include_last_message, sort_by)

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID."""
    return whatsapp_get_chat(chat_jid, include_last_message)

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number."""
    return whatsapp_get_direct_chat_by_contact(sender_phone_number)

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact."""
    return whatsapp_get_contact_chats(jid, limit, page)

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact."""
    return whatsapp_get_last_interaction(jid)

@mcp.tool()
def get_message_context(message_id: str, before: int = 5, after: int = 5) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message."""
    return whatsapp_get_message_context(message_id, before, after)

@mcp.tool()
def send_message(recipient: str, message: str) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group."""
    success, status_message = whatsapp_send_message(recipient, message)
    return {"success": success, "message": status_message}

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file via WhatsApp."""
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {"success": success, "message": status_message}

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send an audio message via WhatsApp."""
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {"success": success, "message": status_message}

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message."""
    file_path = whatsapp_download_media(message_id, chat_jid)
    if file_path:
        return {"success": True, "message": "Media downloaded successfully", "file_path": file_path}
    else:
        return {"success": False, "message": "Failed to download media"}

@mcp.tool()
def mark_as_read(chat_jid: str, message_ids: List[str], sender: Optional[str] = None) -> Dict[str, Any]:
    """Mark WhatsApp messages as read."""
    success, status_message = whatsapp_mark_as_read(chat_jid, message_ids, sender)
    return {"success": success, "message": status_message}

@mcp.tool()
def list_communities(query: Optional[str] = None, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp Communities."""
    return whatsapp_list_communities(query, limit, page)

@mcp.tool()
def get_community_groups(community_jid: str, limit: int = 100, page: int = 0) -> List[Dict[str, Any]]:
    """Get all groups belonging to a specific WhatsApp Community."""
    return whatsapp_get_community_groups(community_jid, limit, page)

@mcp.tool()
def mark_community_as_read(community_jid: str) -> Dict[str, Any]:
    """Mark all messages in all groups of a WhatsApp Community as read.

    NOTE: This only marks messages already in the database.
    Use mark_community_as_read_with_history() to sync history first.
    """
    success, message, details = whatsapp_mark_community_as_read(community_jid)
    return {"success": success, "message": message, "details": details}

# ============================================================================
# NEW HYBRID TOOLS (Combining Go + Baileys)
# ============================================================================

@mcp.tool()
def retrieve_full_history(wait_for_completion: bool = True, timeout: int = 300) -> Dict[str, Any]:
    """
    Retrieve full WhatsApp message history using Baileys.

    This triggers Baileys' syncFullHistory feature which automatically
    downloads all historical messages when connecting to WhatsApp.

    Args:
        wait_for_completion: Whether to wait for sync to complete (default True)
        timeout: Maximum time to wait in seconds (default 300 = 5 minutes)

    Returns:
        Dictionary with sync status and results
    """
    # Check if Baileys is connected
    status = baileys_client.get_sync_status()

    if not status.get("connected"):
        return {
            "success": False,
            "message": "Baileys bridge not connected to WhatsApp. Please scan QR code first.",
            "status": status
        }

    # If already syncing, just return status
    if status.get("is_syncing"):
        return {
            "success": True,
            "message": "History sync already in progress",
            "status": status
        }

    # If already completed, return that info
    if status.get("is_latest") and not status.get("is_syncing"):
        messages_count = status.get("messages_synced", 0)
        return {
            "success": True,
            "message": f"History sync already complete. {messages_count} messages available.",
            "status": status
        }

    # Wait for sync if requested
    if wait_for_completion:
        print("⏳ Waiting for Baileys history sync to complete...")
        success = baileys_client.wait_for_sync_completion(timeout=timeout)

        if success:
            final_status = baileys_client.get_sync_status()
            return {
                "success": True,
                "message": f"History sync complete! {final_status.get('messages_synced', 0)} messages synced.",
                "status": final_status
            }
        else:
            return {
                "success": False,
                "message": "History sync timed out or failed",
                "status": baileys_client.get_sync_status()
            }
    else:
        return {
            "success": True,
            "message": "History sync in progress. Check status with backend_status()",
            "status": status
        }

@mcp.tool()
def sync_history_to_database() -> Dict[str, Any]:
    """
    Manually trigger synchronization of messages from Baileys to Go database.

    This copies all messages from Baileys temp DB to the main Go database,
    enabling them to be marked as read via Go's mark_as_read functionality.

    Returns:
        Dictionary with sync results
    """
    # Call sync_all_chats() to sync messages for ALL chats
    results = sync_all_chats()

    # Aggregate results
    total_synced = 0
    total_deduplicated = 0
    total_chats = len(results)
    failed_chats = 0

    for chat_jid, result in results.items():
        if result.success:
            total_synced += result.messages_synced
            total_deduplicated += result.messages_deduplicated
        else:
            failed_chats += 1

    success = failed_chats == 0

    return {
        "success": success,
        "messages_added": total_synced,
        "messages_deduplicated": total_deduplicated,
        "chats_synced": total_chats,
        "chats_failed": failed_chats,
        "message": f"Synced {total_synced} messages from {total_chats} chats ({failed_chats} failed)" if success
                   else f"Partial sync: {total_synced} messages from {total_chats - failed_chats}/{total_chats} chats"
    }

@mcp.tool()
def mark_community_as_read_with_history(
    community_jid: str,
    sync_timeout: int = 300
) -> Dict[str, Any]:
    """
    THE ULTIMATE HYBRID TOOL: Retrieve history + mark community messages as read.

    This is the complete solution that combines:
    1. Baileys: Retrieve ALL historical messages (works perfectly!)
    2. Sync: Copy messages to Go database
    3. Go: Mark all messages in community as read (works perfectly!)

    This solves the original problem where mark_community_as_read couldn't
    mark historical messages because history sync was broken in whatsmeow.

    Args:
        community_jid: The JID of the community (e.g., "120363143634035041@g.us")
        sync_timeout: Maximum time to wait for history sync (default 300 seconds)

    Returns:
        Complete results from history sync + mark as read operation
    """
    result = {
        "community_jid": community_jid,
        "steps": []
    }

    # Step 1: Check backends health
    print("1️⃣ Checking backend health...")
    status = backend_status()
    if status["overall_status"] != "healthy":
        return {
            "success": False,
            "message": "One or more backends are not healthy",
            "backend_status": status
        }
    result["steps"].append({"step": "health_check", "status": "✅ Both backends healthy"})

    # Step 2: Retrieve history via Baileys
    print("2️⃣ Retrieving full message history via Baileys...")
    history_result = retrieve_full_history(wait_for_completion=True, timeout=sync_timeout)

    if not history_result["success"]:
        result["success"] = False
        result["message"] = f"History sync failed: {history_result['message']}"
        result["steps"].append({"step": "history_sync", "status": f"❌ {history_result['message']}"})
        return result

    messages_synced = history_result["status"].get("messages_synced", 0)
    result["steps"].append({"step": "history_sync", "status": f"✅ {messages_synced} messages retrieved"})

    # Step 3: Sync Baileys → Go database
    print("3️⃣ Syncing messages to Go database...")
    sync_result = sync_history_to_database()

    if not sync_result["success"]:
        result["success"] = False
        result["message"] = f"Database sync failed: {sync_result['message']}"
        result["steps"].append({"step": "database_sync", "status": f"❌ {sync_result['message']}"})
        return result

    messages_added = sync_result["messages_added"]
    messages_skipped = sync_result["messages_skipped"]
    result["steps"].append({
        "step": "database_sync",
        "status": f"✅ {messages_added} new messages, {messages_skipped} already existed"
    })

    # Step 4: Mark community as read via Go
    print("4️⃣ Marking all community messages as read...")
    mark_result = mark_community_as_read(community_jid)

    result["steps"].append({
        "step": "mark_as_read",
        "status": f"{'✅' if mark_result['success'] else '❌'} {mark_result['message']}"
    })
    result["mark_as_read_details"] = mark_result.get("details", {})

    # Step 5: Clean up Baileys temp data
    print("5️⃣ Cleaning up temporary data...")
    if baileys_client.clear_temp_data():
        result["steps"].append({"step": "cleanup", "status": "✅ Temp data cleared"})
    else:
        result["steps"].append({"step": "cleanup", "status": "⚠️ Failed to clear temp data"})

    # Final result
    result["success"] = mark_result["success"]
    result["message"] = f"✅ Complete! History synced and community marked as read. {mark_result['message']}"

    return result

# ============================================================================
# HISTORY SYNC TOOLS (User Story 1.1 - T023)
# ============================================================================

@mcp.tool()
def fetch_history(
    chat_jid: str,
    resume: bool = False,
    max_messages: int = 1000
) -> Dict[str, Any]:
    """
    Start or resume history sync for a specific chat via Baileys.

    Args:
        chat_jid: WhatsApp JID of the chat to sync
        resume: Whether to resume from last checkpoint
        max_messages: Maximum number of messages to fetch (1-10000)

    Returns:
        Dictionary with sync_id and checkpoint status
    """
    try:
        import requests
        response = requests.post(
            f"{baileys_client.BAILEYS_BRIDGE_URL}/history/sync",
            json={
                "chat_jid": chat_jid,
                "resume": resume,
                "max_messages": max_messages
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to start history sync: {str(e)}"
        }

@mcp.tool()
def get_sync_status(chat_jid: str) -> Dict[str, Any]:
    """
    Get current checkpoint status for a chat's history sync.

    Args:
        chat_jid: WhatsApp JID of the chat

    Returns:
        Dictionary with checkpoint details and sync progress
    """
    try:
        import requests
        response = requests.get(
            f"{baileys_client.BAILEYS_BRIDGE_URL}/history/sync/{chat_jid}/status",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "error": f"Failed to get sync status: {str(e)}"
        }

@mcp.tool()
def cancel_sync(chat_jid: str) -> Dict[str, Any]:
    """
    Cancel an ongoing history sync for a chat.

    Args:
        chat_jid: WhatsApp JID of the chat

    Returns:
        Dictionary with cancellation status
    """
    try:
        import requests
        response = requests.post(
            f"{baileys_client.BAILEYS_BRIDGE_URL}/history/sync/{chat_jid}/cancel",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to cancel sync: {str(e)}"
        }

@mcp.tool()
def resume_sync(chat_jid: str, max_messages: int = 1000) -> Dict[str, Any]:
    """
    Resume an interrupted or failed history sync for a chat.

    Args:
        chat_jid: WhatsApp JID of the chat
        max_messages: Maximum number of messages to fetch (1-10000)

    Returns:
        Dictionary with resume status and checkpoint
    """
    try:
        import requests
        response = requests.post(
            f"{baileys_client.BAILEYS_BRIDGE_URL}/history/sync/{chat_jid}/resume",
            json={"max_messages": max_messages},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to resume sync: {str(e)}"
        }

@mcp.tool()
def get_sync_checkpoints() -> Dict[str, Any]:
    """
    Get all sync checkpoints from Go database.

    Returns:
        Dictionary with list of checkpoints for all chats
    """
    try:
        import requests
        # This endpoint would be in Go bridge (T024)
        # For now, return placeholder
        return {
            "checkpoints": [],
            "message": "Checkpoint query endpoint not yet implemented in Go bridge (T024)"
        }
    except Exception as e:
        return {
            "error": f"Failed to get checkpoints: {str(e)}"
        }

@mcp.tool()
def clear_temp_storage() -> Dict[str, Any]:
    """
    Clear all data from Baileys temp database.

    Should be called after successful sync to Go database.

    Returns:
        Dictionary with clear status
    """
    try:
        import requests
        # This endpoint would clear Baileys temp DB
        # For now, return placeholder
        return {
            "success": True,
            "message": "Temp storage clear endpoint not yet implemented in Baileys bridge"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear temp storage: {str(e)}"
        }

# ============================================================================
# MESSAGE QUERY TOOLS (User Story 1.2 - T025)
# ============================================================================

@mcp.tool()
def query_synced_messages(
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
    """
    Query synced messages from Go database with various filters.

    This allows searching through all historical messages that have been
    synced to the Go database (either from Baileys or from real-time messages).

    Args:
        chat_jid: Filter by specific chat JID
        sender: Filter by sender (partial match supported)
        content: Search in message content (partial match supported)
        after_time: Only messages after this time (ISO 8601 format)
        before_time: Only messages before this time (ISO 8601 format)
        limit: Maximum number of messages to return (default 100, max varies by server)
        offset: Number of messages to skip (for pagination)
        include_media: Whether to include media messages (default False = text only)
        media_type: Filter by specific media type (image, video, audio, document)

    Returns:
        Dictionary with:
        - success: Whether the query succeeded
        - messages: List of matching messages
        - total: Total number of matching messages (for pagination)
        - limit: Limit used in query
        - offset: Offset used in query

    Example:
        # Search for messages containing "hello" in a specific chat
        query_synced_messages(chat_jid="123456789@g.us", content="hello", limit=50)

        # Get all messages from a specific sender
        query_synced_messages(sender="1234567890")

        # Get recent messages with media
        query_synced_messages(
            after_time="2025-01-01T00:00:00Z",
            include_media=True,
            media_type="image"
        )
    """
    return go_client.query_messages(
        chat_jid=chat_jid,
        sender=sender,
        content=content,
        after_time=after_time,
        before_time=before_time,
        limit=limit,
        offset=offset,
        include_media=include_media,
        media_type=media_type
    )


@mcp.tool()
def get_message_statistics() -> Dict[str, Any]:
    """
    Get comprehensive statistics about all synced messages in the Go database.

    Returns detailed metrics including:
    - Total number of messages synced
    - Total number of chats
    - Total number of contacts
    - Number of media messages vs text messages
    - Breakdown by media type (image, video, audio, document)
    - Oldest and newest message timestamps

    Returns:
        Dictionary with complete message statistics

    Example response:
        {
            "success": True,
            "total_messages": 15234,
            "total_chats": 89,
            "total_contacts": 156,
            "media_messages": 3421,
            "text_messages": 11813,
            "messages_by_type": {
                "image": 2145,
                "video": 876,
                "audio": 234,
                "document": 166
            },
            "oldest_message": "2023-06-15T10:23:45Z",
            "newest_message": "2025-10-10T14:32:11Z"
        }
    """
    return go_client.get_message_stats()


# ============================================================================
# BAILEYS-SPECIFIC TOOLS
# ============================================================================

@mcp.tool()
def get_baileys_sync_status() -> Dict[str, Any]:
    """Get current Baileys history sync status."""
    return baileys_client.get_sync_status()

@mcp.tool()
def clear_baileys_temp_data() -> Dict[str, Any]:
    """Clear Baileys temporary data (after successful sync)."""
    success = baileys_client.clear_temp_data()
    return {
        "success": success,
        "message": "Temp data cleared" if success else "Failed to clear temp data"
    }

# ============================================================================
# T043: MESSAGING MCP TOOLS (15 tools routing to Go bridge)
# ============================================================================

@mcp.tool()
def send_text_message_v2(chat_jid: str, text: str) -> Dict[str, Any]:
    """
    Send a text message to a WhatsApp chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the recipient (person or group)
        text: The text message to send

    Returns:
        Dictionary with success status and message
    """
    success, message = go.send_text_message(chat_jid, text)
    return {"success": success, "message": message}


@mcp.tool()
def send_media_message_v2(
    chat_jid: str,
    media_path: str,
    media_type: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a media message (image, video, audio, document) via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the recipient
        media_path: Path to the media file on server
        media_type: Type of media (image, video, audio, document)
        caption: Optional caption for the media

    Returns:
        Dictionary with success status and message
    """
    success, message = go.send_media_message(chat_jid, media_path, media_type, caption)
    return {"success": success, "message": message}


@mcp.tool()
def send_voice_note_v2(chat_jid: str, audio_path: str) -> Dict[str, Any]:
    """
    Send a voice note via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the recipient
        audio_path: Path to the audio file on server

    Returns:
        Dictionary with success status and message
    """
    success, message = go.send_voice_note(chat_jid, audio_path)
    return {"success": success, "message": message}


@mcp.tool()
def send_sticker_v2(chat_jid: str, sticker_path: str) -> Dict[str, Any]:
    """
    Send a sticker via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the recipient
        sticker_path: Path to the sticker file on server

    Returns:
        Dictionary with success status and message
    """
    success, message = go.send_sticker(chat_jid, sticker_path)
    return {"success": success, "message": message}


@mcp.tool()
def send_contact_v2(chat_jid: str, vcard: str) -> Dict[str, Any]:
    """
    Send a contact vCard via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the recipient
        vcard: vCard string in standard format

    Returns:
        Dictionary with success status and message
    """
    success, message = go.send_contact(chat_jid, vcard)
    return {"success": success, "message": message}


@mcp.tool()
def send_location_v2(chat_jid: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Send a GPS location via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the recipient
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Dictionary with success status and message
    """
    success, message = go.send_location(chat_jid, latitude, longitude)
    return {"success": success, "message": message}


@mcp.tool()
def react_to_message_v2(chat_jid: str, message_id: str, emoji: str) -> Dict[str, Any]:
    """
    React to a message with an emoji via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat containing the message
        message_id: ID of the message to react to
        emoji: Emoji to use for reaction

    Returns:
        Dictionary with success status and message
    """
    success, message = go.react_to_message(chat_jid, message_id, emoji)
    return {"success": success, "message": message}


@mcp.tool()
def edit_message_v2(message_id: str, new_text: str) -> Dict[str, Any]:
    """
    Edit a previously sent message via Go bridge.

    Args:
        message_id: ID of the message to edit
        new_text: New text content for the message

    Returns:
        Dictionary with success status and message
    """
    success, message = go.edit_message(message_id, new_text)
    return {"success": success, "message": message}


@mcp.tool()
def delete_message_v2(message_id: str) -> Dict[str, Any]:
    """
    Delete/revoke a message via Go bridge.

    Args:
        message_id: ID of the message to delete

    Returns:
        Dictionary with success status and message
    """
    success, message = go.delete_message(message_id)
    return {"success": success, "message": message}


@mcp.tool()
def forward_message_v2(message_id: str, to_chat_jid: str) -> Dict[str, Any]:
    """
    Forward a message to another chat via Go bridge.

    Args:
        message_id: ID of the message to forward
        to_chat_jid: WhatsApp JID of the destination chat

    Returns:
        Dictionary with success status and message
    """
    success, message = go.forward_message(message_id, to_chat_jid)
    return {"success": success, "message": message}


@mcp.tool()
def download_media_v2(message_id: str) -> Dict[str, Any]:
    """
    Download media from a message via Go bridge.

    Args:
        message_id: ID of the message containing media

    Returns:
        Dictionary with success status and file path
    """
    # Use existing go_client.download_media function
    # Note: It requires chat_jid, but we'll use empty string as placeholder
    # The Go endpoint should handle message_id alone
    file_path = go_client.download_media(message_id, "")
    if file_path:
        return {"success": True, "message": "Media downloaded", "file_path": file_path}
    else:
        return {"success": False, "message": "Failed to download media"}


@mcp.tool()
def mark_message_read_v2(chat_jid: str, message_id: str) -> Dict[str, Any]:
    """
    Mark a specific message as read via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat
        message_id: ID of the message to mark as read

    Returns:
        Dictionary with success status and message
    """
    # Phase 3: T012 - Updated to handle new 4-value return (includes count and error_code)
    success, message, count, error_code = go_client.mark_as_read(chat_jid, [message_id])
    result = {"success": success, "message": message, "count": count}
    if error_code:
        result["error_code"] = error_code
    return result


@mcp.tool()
def mark_chat_read_v2(chat_jid: str) -> Dict[str, Any]:
    """
    Mark all messages in a chat as read via Go bridge.

    Phase 3: T011-T013 - Fixed to properly handle mark-all functionality with structured responses.

    Args:
        chat_jid: WhatsApp JID of the chat

    Returns:
        Dictionary with success status, message, count, and optional error_code
    """
    # Phase 3: T012 - Updated to handle new 4-value return (includes count and error_code)
    success, message, count, error_code = go_client.mark_as_read(chat_jid, [])
    result = {"success": success, "message": message, "count": count}

    # Phase 3: T013 - Handle EMPTY_CHAT case (which is success=true but count=0)
    if error_code:
        result["error_code"] = error_code
        if error_code == "EMPTY_CHAT":
            # This is not an error - just informational
            result["message"] = "Chat has no messages to mark as read"

    return result


@mcp.tool()
def list_chats_v2(limit: int = 20, archived: bool = False) -> Dict[str, Any]:
    """
    List WhatsApp chats via Go bridge.

    Args:
        limit: Maximum number of chats to return
        archived: Whether to include archived chats

    Returns:
        Dictionary with list of chats
    """
    chats = go.list_chats(limit, archived)
    return {"success": True, "chats": chats, "count": len(chats)}


@mcp.tool()
def get_chat_metadata_v2(chat_jid: str) -> Dict[str, Any]:
    """
    Get metadata for a specific chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat

    Returns:
        Dictionary with chat metadata
    """
    return go.get_chat_metadata(chat_jid)


# ============================================================================
# T044: CHAT MANAGEMENT MCP TOOLS (6 tools routing to Go bridge)
# ============================================================================

@mcp.tool()
def archive_chat(chat_jid: str) -> Dict[str, Any]:
    """
    Archive a WhatsApp chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat to archive

    Returns:
        Dictionary with success status and message
    """
    success, message = go.archive_chat(chat_jid)
    return {"success": success, "message": message}


@mcp.tool()
def unarchive_chat(chat_jid: str) -> Dict[str, Any]:
    """
    Unarchive a WhatsApp chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat to unarchive

    Returns:
        Dictionary with success status and message
    """
    success, message = go.unarchive_chat(chat_jid)
    return {"success": success, "message": message}


@mcp.tool()
def pin_chat(chat_jid: str) -> Dict[str, Any]:
    """
    Pin a WhatsApp chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat to pin

    Returns:
        Dictionary with success status and message
    """
    success, message = go.pin_chat(chat_jid)
    return {"success": success, "message": message}


@mcp.tool()
def unpin_chat(chat_jid: str) -> Dict[str, Any]:
    """
    Unpin a WhatsApp chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat to unpin

    Returns:
        Dictionary with success status and message
    """
    success, message = go.unpin_chat(chat_jid)
    return {"success": success, "message": message}


@mcp.tool()
def mute_chat(chat_jid: str, duration_seconds: int = 0) -> Dict[str, Any]:
    """
    Mute notifications for a WhatsApp chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat to mute
        duration_seconds: Duration in seconds (0 = mute forever)

    Returns:
        Dictionary with success status and message
    """
    success, message = go.mute_chat(chat_jid, duration_seconds)
    return {"success": success, "message": message}


@mcp.tool()
def unmute_chat(chat_jid: str) -> Dict[str, Any]:
    """
    Unmute notifications for a WhatsApp chat via Go bridge.

    Args:
        chat_jid: WhatsApp JID of the chat to unmute

    Returns:
        Dictionary with success status and message
    """
    success, message = go.unmute_chat(chat_jid)
    return {"success": success, "message": message}


# ============================================================================
# T045: CONTACT MCP TOOLS (8 tools routing to Go bridge)
# ============================================================================

@mcp.tool()
def search_contacts_v2(query: str) -> Dict[str, Any]:
    """
    Search WhatsApp contacts by name or phone number via Go bridge.

    Args:
        query: Search query (name or phone number)

    Returns:
        Dictionary with list of matching contacts
    """
    contacts = go.search_contacts_v2(query)
    return {"success": True, "contacts": contacts, "count": len(contacts)}


@mcp.tool()
def get_contact_details_v2(jid: str) -> Dict[str, Any]:
    """
    Get detailed information about a WhatsApp contact via Go bridge.

    Args:
        jid: WhatsApp JID of the contact

    Returns:
        Dictionary with contact details
    """
    return go.get_contact_details(jid)


@mcp.tool()
def check_is_on_whatsapp(phone: str) -> Dict[str, Any]:
    """
    Check if a phone number is registered on WhatsApp via Go bridge.

    Args:
        phone: Phone number to check (with country code)

    Returns:
        Dictionary with WhatsApp status
    """
    return go.check_is_on_whatsapp(phone)


@mcp.tool()
def get_profile_picture_v2(jid: str) -> Dict[str, Any]:
    """
    Get profile picture URL for a contact via Go bridge.

    Args:
        jid: WhatsApp JID of the contact

    Returns:
        Dictionary with profile picture URL
    """
    return go.get_profile_picture(jid)


@mcp.tool()
def update_profile_picture_v2(image_path: str) -> Dict[str, Any]:
    """
    Update own profile picture via Go bridge.

    Args:
        image_path: Path to the image file on server

    Returns:
        Dictionary with success status and message
    """
    success, message = go.update_profile_picture(image_path)
    return {"success": success, "message": message}


@mcp.tool()
def get_contact_status_v2(jid: str) -> Dict[str, Any]:
    """
    Get status message for a contact via Go bridge.

    Args:
        jid: WhatsApp JID of the contact

    Returns:
        Dictionary with status message
    """
    return go.get_contact_status(jid)


@mcp.tool()
def update_profile_status_v2(status_text: str) -> Dict[str, Any]:
    """
    Update own WhatsApp status message via Go bridge.

    Args:
        status_text: New status message text

    Returns:
        Dictionary with success status and message
    """
    success, message = go.update_profile_status(status_text)
    return {"success": success, "message": message, "status_text": status_text}


@mcp.tool()
def get_linked_devices_v2() -> Dict[str, Any]:
    """
    Get list of linked WhatsApp devices via Go bridge.

    Returns:
        Dictionary with list of linked devices
    """
    return go.get_linked_devices()


# ============================================================================
# T049: PRIVACY MCP TOOLS (8 tools routing to Go bridge)
# ============================================================================

@mcp.tool()
def block_contact(jid: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
    """
    Block a WhatsApp contact via Go bridge.

    Args:
        jid: WhatsApp JID of the contact (optional if phone provided)
        phone: Phone number of the contact (optional if jid provided)

    Returns:
        Dictionary with success status and message
    """
    success, message = go.block_contact(jid, phone)
    return {"success": success, "message": message}


@mcp.tool()
def unblock_contact(jid: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
    """
    Unblock a WhatsApp contact via Go bridge.

    Args:
        jid: WhatsApp JID of the contact (optional if phone provided)
        phone: Phone number of the contact (optional if jid provided)

    Returns:
        Dictionary with success status and message
    """
    success, message = go.unblock_contact(jid, phone)
    return {"success": success, "message": message}


@mcp.tool()
def get_blocked_contacts() -> Dict[str, Any]:
    """
    Get list of all blocked WhatsApp contacts via Go bridge.

    Returns:
        Dictionary with list of blocked contacts
    """
    return go.get_blocked_contacts()


@mcp.tool()
def get_privacy_settings() -> Dict[str, Any]:
    """
    Get all WhatsApp privacy settings via Go bridge.

    Returns:
        Dictionary with privacy settings (last_seen, profile_picture, status, online, etc.)
    """
    return go.get_privacy_settings()


@mcp.tool()
def update_last_seen_privacy(value: str) -> Dict[str, Any]:
    """
    Update last seen privacy setting via Go bridge.

    Args:
        value: Privacy level ('all', 'contacts', 'match_last_seen', 'none')

    Returns:
        Dictionary with success status and message
    """
    success, message = go.update_last_seen_privacy(value)
    return {"success": success, "message": message, "setting": "last_seen", "value": value}


@mcp.tool()
def update_profile_picture_privacy(value: str) -> Dict[str, Any]:
    """
    Update profile picture privacy setting via Go bridge.

    Args:
        value: Privacy level ('all', 'contacts', 'match_last_seen', 'none')

    Returns:
        Dictionary with success status and message
    """
    success, message = go.update_profile_picture_privacy(value)
    return {"success": success, "message": message, "setting": "profile_picture", "value": value}


@mcp.tool()
def update_status_privacy(value: str) -> Dict[str, Any]:
    """
    Update status privacy setting via Go bridge.

    Args:
        value: Privacy level ('all', 'contacts', 'match_last_seen', 'none')

    Returns:
        Dictionary with success status and message
    """
    success, message = go.update_status_privacy(value)
    return {"success": success, "message": message, "setting": "status", "value": value}


@mcp.tool()
def update_online_privacy(value: str) -> Dict[str, Any]:
    """
    Update online privacy setting via Go bridge.

    Args:
        value: Privacy level ('all', 'match_last_seen')

    Returns:
        Dictionary with success status and message
    """
    success, message = go.update_online_privacy(value)
    return {"success": success, "message": message, "setting": "online", "value": value}


# ============================================================================
# T053: BUSINESS MCP TOOLS (3 tools routing to Go/Baileys bridges)
# ============================================================================

@mcp.tool()
def get_business_profile(jid: str) -> Dict[str, Any]:
    """
    Get business profile information via Go bridge.

    Args:
        jid: WhatsApp JID of the business account

    Returns:
        Dictionary with business profile details (description, category, address, website, email)
    """
    return go.get_business_profile(jid)


@mcp.tool()
def get_business_catalog(jid: str) -> Dict[str, Any]:
    """
    Get business product catalog via Baileys bridge (BAILEYS_EXCLUSIVE).

    Args:
        jid: WhatsApp JID of the business account

    Returns:
        Dictionary with catalog information and product count
    """
    import backends.baileys_client as baileys
    return baileys.get_business_catalog(jid)


@mcp.tool()
def get_product_details(jid: str, product_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific product from business catalog via Baileys bridge (BAILEYS_EXCLUSIVE).

    Args:
        jid: WhatsApp JID of the business account
        product_id: Product ID to retrieve

    Returns:
        Dictionary with product details (name, description, price, images, availability)
    """
    import backends.baileys_client as baileys
    return baileys.get_product_details(jid, product_id)


# ============================================================================
# T055: NEWSLETTER MCP TOOLS (5 tools routing to Go bridge)
# ============================================================================

@mcp.tool()
def subscribe_to_newsletter(jid: str) -> Dict[str, Any]:
    """
    Subscribe to a WhatsApp newsletter via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter

    Returns:
        Dictionary with success status and message
    """
    success, message = go.subscribe_to_newsletter(jid)
    return {"success": success, "message": message, "jid": jid if success else None}


@mcp.tool()
def unsubscribe_from_newsletter(jid: str) -> Dict[str, Any]:
    """
    Unsubscribe from a WhatsApp newsletter via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter

    Returns:
        Dictionary with success status and message
    """
    success, message = go.unsubscribe_from_newsletter(jid)
    return {"success": success, "message": message, "jid": jid if success else None}


@mcp.tool()
def create_newsletter(name: str, description: str = "") -> Dict[str, Any]:
    """
    Create a new WhatsApp newsletter via Go bridge.

    Args:
        name: Newsletter name (required)
        description: Newsletter description (optional)

    Returns:
        Dictionary with creation result, newsletter JID, and invite URL
    """
    return go.create_newsletter(name, description)


@mcp.tool()
def get_newsletter_info(jid: str) -> Dict[str, Any]:
    """
    Get metadata and information about a WhatsApp newsletter via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter

    Returns:
        Dictionary with newsletter metadata (name, description, subscriber count, creation time, owner, etc.)
    """
    return go.get_newsletter_metadata(jid)


@mcp.tool()
def react_to_newsletter_post(jid: str, message_id: str, emoji: str) -> Dict[str, Any]:
    """
    React to a newsletter post with an emoji via Go bridge.

    Args:
        jid: WhatsApp JID of the newsletter
        message_id: ID of the newsletter message/post to react to
        emoji: Emoji to react with (e.g., "👍", "❤️", "🔥")

    Returns:
        Dictionary with success status and message
    """
    success, message = go.react_to_newsletter_message(jid, message_id, emoji)
    return {"success": success, "message": message, "message_id": message_id if success else None}


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Unified WhatsApp MCP Server...")
    print("   - Go Bridge: http://localhost:8080")
    print("   - Baileys Bridge: http://localhost:8081")
    print("   - Unified MCP: stdio transport")
    print("\n💡 Key Features:")
    print("   ✅ All Go/whatsmeow features (communities, mark as read, media)")
    print("   ✅ Baileys history sync (working!)")
    print("   ✅ Hybrid: mark_community_as_read_with_history()")
    print("\n")

    # Check backends on startup
    status = backend_status()
    print(f"Backend Status: {status['overall_status']}")
    print(f"  Go: {'✅ Healthy' if status['go_bridge']['healthy'] else '❌ Unhealthy'}")
    print(f"  Baileys: {'✅ Healthy' if status['baileys_bridge']['healthy'] else '❌ Unhealthy'}")
    print("\n")

    # Run the server
    mcp.run(transport='stdio')
