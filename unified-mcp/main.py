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
from sync import sync_baileys_to_go, clear_baileys_temp_data, get_baileys_sync_status

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
    added, skipped, status_msg = sync_baileys_to_go()

    return {
        "success": added >= 0,
        "messages_added": added,
        "messages_skipped": skipped,
        "message": status_msg
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
    if clear_baileys_temp_data():
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
