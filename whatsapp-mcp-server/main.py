from typing import List, Dict, Any, Optional
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
    sync_chat_history as whatsapp_sync_chat_history,
    list_communities_go_api as whatsapp_list_communities,
    get_community_groups_go_api as whatsapp_get_community_groups,
    mark_community_as_read_go_api as whatsapp_mark_community_as_read,
    create_poll_v2_baileys_api as whatsapp_create_poll_v2,
    create_poll_v3_baileys_api as whatsapp_create_poll_v3,
    vote_poll_baileys_api as whatsapp_vote_poll,
    get_poll_results_baileys_api as whatsapp_get_poll_results,
    post_status_baileys_api as whatsapp_post_status,
    list_status_baileys_api as whatsapp_list_status,
    view_status_baileys_api as whatsapp_view_status,
    get_status_privacy_baileys_api as whatsapp_get_status_privacy,
    create_group_go_api as whatsapp_create_group,
    update_group_metadata_go_api as whatsapp_update_group_metadata,
    add_group_participants_go_api as whatsapp_add_group_participants,
    remove_group_participants_go_api as whatsapp_remove_group_participants,
    promote_group_participants_go_api as whatsapp_promote_group_participants,
    demote_group_participants_go_api as whatsapp_demote_group_participants,
    get_group_participants_go_api as whatsapp_get_group_participants,
    get_group_invite_link_go_api as whatsapp_get_group_invite_link,
    revoke_group_invite_link_go_api as whatsapp_revoke_group_invite_link
)

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

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
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

@mcp.tool()
def send_message(
    recipient: str,
    message: str
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
    
    Returns:
        A dictionary containing success status and a status message
    """
    # Validate input
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }
    
    # Call the whatsapp_send_message function with the unified recipient parameter
    success, status_message = whatsapp_send_message(recipient, message)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
    
    Returns:
        A dictionary containing success status and a status message
    """
    
    # Call the whatsapp_send_file function
    success, status_message = whatsapp_send_file(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.

    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message

    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)

    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

@mcp.tool()
def mark_as_read(
    chat_jid: str,
    message_ids: List[str],
    sender: Optional[str] = None
) -> Dict[str, Any]:
    """Mark WhatsApp messages as read.

    Args:
        chat_jid: The JID of the chat containing the messages
        message_ids: List of message IDs to mark as read
        sender: Optional sender JID (required for group chats when marking messages from specific senders)

    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_mark_as_read(chat_jid, message_ids, sender)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def list_communities(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0
) -> List[Dict[str, Any]]:
    """Get all WhatsApp Communities.

    Args:
        query: Optional search term to filter communities by name
        limit: Maximum number of communities to return (default 20)
        page: Page number for pagination (default 0)

    Returns:
        List of community dictionaries with group counts
    """
    success, message, communities = whatsapp_list_communities(query, limit)
    if not success:
        return []
    return communities

@mcp.tool()
def get_community_groups(
    community_jid: str,
    limit: int = 100,
    page: int = 0
) -> List[Dict[str, Any]]:
    """Get all groups belonging to a specific WhatsApp Community.

    Args:
        community_jid: The JID of the community
        limit: Maximum number of groups to return (default 100)
        page: Page number for pagination (default 0)

    Returns:
        List of chat dictionaries for groups in the community
    """
    success, message, groups = whatsapp_get_community_groups(community_jid, limit)
    if not success:
        return []
    return groups

@mcp.tool()
def mark_community_as_read(community_jid: str) -> Dict[str, Any]:
    """Mark all messages in all groups of a WhatsApp Community as read.

    Args:
        community_jid: The JID of the community

    Returns:
        A dictionary containing success status, overall message, and per-group details
    """
    success, message, details = whatsapp_mark_community_as_read(community_jid)
    return {
        "success": success,
        "message": message,
        "details": details
    }

@mcp.tool()
def sync_and_mark_community_read(
    community_jid: str,
    history_count: int = 50
) -> Dict[str, Any]:
    """Sync history for all groups in a community, then mark all as read.

    This is a hybrid workflow that:
    1. Gets all groups in the community
    2. Syncs message history for each group
    3. Marks all groups in the community as read
    4. Returns combined results with continue-on-error handling

    Args:
        community_jid: The JID of the community
        history_count: Number of messages to sync per group (default 50)

    Returns:
        A dictionary containing:
        - success: Overall success status
        - message: Summary message
        - history_sync: Per-group sync results {group_jid: {success, message}}
        - mark_read: Mark-as-read operation results
    """
    result = {
        "success": False,
        "message": "",
        "history_sync": {},
        "mark_read": {}
    }

    # Step 1: Get all groups in the community
    success, message, groups = whatsapp_get_community_groups(community_jid, limit=100)
    if not success or not groups:
        result["message"] = f"Failed to get community groups: {message}"
        return result

    # Step 2: Sync history for each group (continue on error)
    sync_success_count = 0
    sync_fail_count = 0

    for group in groups:
        group_jid = group.get("jid")
        group_name = group.get("name", group_jid)

        if not group_jid:
            continue

        # Sync history for this group
        sync_success, sync_message = whatsapp_sync_chat_history(group_jid, history_count)

        result["history_sync"][group_name] = {
            "jid": group_jid,
            "success": sync_success,
            "message": sync_message
        }

        if sync_success:
            sync_success_count += 1
        else:
            sync_fail_count += 1

    # Step 3: Mark all groups as read
    mark_success, mark_message, mark_details = whatsapp_mark_community_as_read(community_jid)

    result["mark_read"] = {
        "success": mark_success,
        "message": mark_message,
        "details": mark_details
    }

    # Step 4: Build overall result
    total_groups = len(groups)
    result["success"] = sync_success_count > 0 and mark_success
    result["message"] = (
        f"Community workflow completed: "
        f"{sync_success_count}/{total_groups} groups synced, "
        f"{sync_fail_count} failed. "
        f"Mark as read: {mark_message}"
    )

    return result

@mcp.tool()
def create_poll_single_choice(
    chat_jid: str,
    question: str,
    options: List[str]
) -> Dict[str, Any]:
    """Create a single-choice poll in a WhatsApp chat.

    Args:
        chat_jid: The JID of the chat to send the poll to (group or direct chat)
        question: The poll question
        options: List of poll options (2-12 items)

    Returns:
        A dictionary containing success status, message, and poll details (message_id, etc.)
    """
    success, message, result = whatsapp_create_poll_v2(chat_jid, question, options)

    if success and result:
        return {
            "success": True,
            "message": message,
            "message_id": result.get("message_id"),
            "chat_jid": result.get("chat_jid"),
            "poll_type": result.get("poll_type"),
            "selectable_count": result.get("selectable_count")
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def create_poll_multiple_choice(
    chat_jid: str,
    question: str,
    options: List[str],
    allow_multiple: bool = True,
    max_selections: Optional[int] = None
) -> Dict[str, Any]:
    """Create a multiple-choice poll in a WhatsApp chat.

    Args:
        chat_jid: The JID of the chat to send the poll to (group or direct chat)
        question: The poll question
        options: List of poll options (2-12 items)
        allow_multiple: Whether to allow multiple selections (default True)
        max_selections: Maximum number of selections allowed (default None = all options)

    Returns:
        A dictionary containing success status, message, and poll details (message_id, etc.)
    """
    success, message, result = whatsapp_create_poll_v3(
        chat_jid, question, options, allow_multiple, max_selections
    )

    if success and result:
        return {
            "success": True,
            "message": message,
            "message_id": result.get("message_id"),
            "chat_jid": result.get("chat_jid"),
            "poll_type": result.get("poll_type"),
            "selectable_count": result.get("selectable_count"),
            "allow_multiple": result.get("allow_multiple")
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def vote_on_poll(
    chat_jid: str,
    message_id: str,
    option_indices: List[int]
) -> Dict[str, Any]:
    """Vote on a WhatsApp poll.

    Args:
        chat_jid: The JID of the chat containing the poll
        message_id: The message ID of the poll
        option_indices: List of option indices to vote for (0-based, e.g., [0] for first option)

    Returns:
        A dictionary containing success status, message, and vote confirmation
    """
    success, message, result = whatsapp_vote_poll(chat_jid, message_id, option_indices)

    if success and result:
        return {
            "success": True,
            "message": message,
            "message_id": result.get("message_id"),
            "chat_jid": result.get("chat_jid"),
            "voted_options": result.get("voted_options")
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def get_poll_results(
    chat_jid: str,
    message_id: str
) -> Dict[str, Any]:
    """Get results of a WhatsApp poll.

    Args:
        chat_jid: The JID of the chat containing the poll
        message_id: The message ID of the poll

    Returns:
        A dictionary containing success status, message, and poll results
    """
    success, message, result = whatsapp_get_poll_results(chat_jid, message_id)

    if success and result:
        return {
            "success": True,
            "message": message,
            "data": result
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def post_status(
    text: Optional[str] = None,
    media_path: Optional[str] = None,
    background_color: Optional[str] = None
) -> Dict[str, Any]:
    """Post a WhatsApp Status update (Story).

    Args:
        text: Optional text content for the status
        media_path: Optional absolute path to media file (image/video)
        background_color: Optional background color for text status (hex format, e.g., '#FF5733')

    Returns:
        A dictionary containing success status, message, and status details
    """
    success, message, result = whatsapp_post_status(text, media_path, background_color)

    if success and result:
        return {
            "success": True,
            "message": message,
            "status_id": result.get("status_id"),
            "timestamp": result.get("timestamp")
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def list_status_updates(limit: int = 50) -> List[Dict[str, Any]]:
    """Get WhatsApp Status updates from contacts.

    Args:
        limit: Maximum number of statuses to return (default 50)

    Returns:
        A list of status update dictionaries
    """
    success, message, statuses = whatsapp_list_status(limit)

    if success:
        return statuses
    else:
        # Return empty list with error note
        return []

@mcp.tool()
def view_status(
    status_id: str,
    owner_jid: str
) -> Dict[str, Any]:
    """Mark a WhatsApp Status as viewed.

    Args:
        status_id: The message ID of the status
        owner_jid: The JID of the person who posted the status

    Returns:
        A dictionary containing success status and confirmation message
    """
    success, message, result = whatsapp_view_status(status_id, owner_jid)

    if success and result:
        return {
            "success": True,
            "message": message,
            "status_id": result.get("status_id"),
            "owner_jid": result.get("owner_jid")
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def get_status_privacy() -> Dict[str, Any]:
    """Get WhatsApp Status privacy settings.

    Returns:
        A dictionary containing privacy settings information
    """
    success, message, privacy = whatsapp_get_status_privacy()

    if success and privacy:
        return {
            "success": True,
            "message": message,
            "privacy": privacy
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def create_group(
    name: str,
    participants: List[str]
) -> Dict[str, Any]:
    """Create a new WhatsApp group.

    Args:
        name: The name of the group
        participants: List of participant phone numbers (with country code, no +) or JIDs

    Returns:
        A dictionary containing success status, message, and group_jid if successful
    """
    success, message, group_jid = whatsapp_create_group(name, participants)

    if success and group_jid:
        return {
            "success": True,
            "message": message,
            "group_jid": group_jid
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def update_group_metadata(
    group_jid: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    picture: Optional[str] = None
) -> Dict[str, Any]:
    """Update WhatsApp group metadata (name, description, or picture).

    Args:
        group_jid: The JID of the group
        name: Optional new group name
        description: Optional new group description
        picture: Optional path to new group picture

    Returns:
        A dictionary containing success status and message
    """
    success, message = whatsapp_update_group_metadata(group_jid, name, description, picture)

    return {
        "success": success,
        "message": message
    }

@mcp.tool()
def add_group_participants(
    group_jid: str,
    participants: List[str]
) -> Dict[str, Any]:
    """Add participants to a WhatsApp group.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers (with country code, no +) or JIDs to add

    Returns:
        A dictionary containing success status, message, and per-participant results
    """
    success, message, results = whatsapp_add_group_participants(group_jid, participants)

    return {
        "success": success,
        "message": message,
        "results": results
    }

@mcp.tool()
def remove_group_participants(
    group_jid: str,
    participants: List[str]
) -> Dict[str, Any]:
    """Remove participants from a WhatsApp group.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers (with country code, no +) or JIDs to remove

    Returns:
        A dictionary containing success status, message, and per-participant results
    """
    success, message, results = whatsapp_remove_group_participants(group_jid, participants)

    return {
        "success": success,
        "message": message,
        "results": results
    }

@mcp.tool()
def promote_group_participants(
    group_jid: str,
    participants: List[str]
) -> Dict[str, Any]:
    """Promote participants to admins in a WhatsApp group.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers (with country code, no +) or JIDs to promote

    Returns:
        A dictionary containing success status, message, and per-participant results
    """
    success, message, results = whatsapp_promote_group_participants(group_jid, participants)

    return {
        "success": success,
        "message": message,
        "results": results
    }

@mcp.tool()
def demote_group_participants(
    group_jid: str,
    participants: List[str]
) -> Dict[str, Any]:
    """Demote participants from admins to members in a WhatsApp group.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers (with country code, no +) or JIDs to demote

    Returns:
        A dictionary containing success status, message, and per-participant results
    """
    success, message, results = whatsapp_demote_group_participants(group_jid, participants)

    return {
        "success": success,
        "message": message,
        "results": results
    }

@mcp.tool()
def get_group_participants(
    group_jid: str
) -> List[Dict[str, Any]]:
    """Get all participants in a WhatsApp group.

    Args:
        group_jid: The JID of the group

    Returns:
        A list of participant dictionaries with JID, admin status, and super-admin status
    """
    success, message, participants = whatsapp_get_group_participants(group_jid)

    if success:
        return participants
    else:
        # Return empty list with error note
        return []

@mcp.tool()
def get_group_invite_link(
    group_jid: str
) -> Dict[str, Any]:
    """Get the invite link for a WhatsApp group.

    Args:
        group_jid: The JID of the group

    Returns:
        A dictionary containing success status, message, and invite_link if successful
    """
    success, message, invite_link = whatsapp_get_group_invite_link(group_jid)

    if success and invite_link:
        return {
            "success": True,
            "message": message,
            "invite_link": invite_link
        }
    else:
        return {
            "success": False,
            "message": message
        }

@mcp.tool()
def revoke_group_invite_link(
    group_jid: str
) -> Dict[str, Any]:
    """Revoke and regenerate the invite link for a WhatsApp group.

    Args:
        group_jid: The JID of the group

    Returns:
        A dictionary containing success status, message, and new_invite_link if successful
    """
    success, message, new_invite_link = whatsapp_revoke_group_invite_link(group_jid)

    if success and new_invite_link:
        return {
            "success": True,
            "message": message,
            "invite_link": new_invite_link
        }
    else:
        return {
            "success": False,
            "message": message
        }

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')