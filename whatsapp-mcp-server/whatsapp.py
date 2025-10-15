import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple, Dict, Any
import os.path
import requests
import json
import audio

MESSAGES_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'whatsapp-bridge', 'store', 'messages.db')
WHATSAPP_API_BASE_URL = "http://localhost:8080/api"
BAILEYS_API_BASE_URL = "http://localhost:8081/api"

@dataclass
class Message:
    timestamp: datetime
    sender: str
    content: str
    is_from_me: bool
    chat_jid: str
    id: str
    chat_name: Optional[str] = None
    sender_name: Optional[str] = None
    media_type: Optional[str] = None

@dataclass
class Chat:
    jid: str
    name: Optional[str]
    last_message_time: Optional[datetime]
    last_message: Optional[str] = None
    last_sender: Optional[str] = None
    last_is_from_me: Optional[bool] = None
    parent_group_jid: Optional[str] = None

    @property
    def is_group(self) -> bool:
        """Determine if chat is a group based on JID pattern."""
        return self.jid.endswith("@g.us")

    @property
    def is_community(self) -> bool:
        """Determine if chat is a community based on JID pattern."""
        return self.jid.endswith("@newsletter")

    @property
    def is_community_group(self) -> bool:
        """Determine if this group belongs to a community."""
        return self.parent_group_jid is not None

@dataclass
class Contact:
    phone_number: str
    name: Optional[str]
    jid: str

@dataclass
class Community:
    jid: str
    name: Optional[str]
    group_count: int = 0
    groups: List[Dict[str, Any]] = None

@dataclass
class MessageContext:
    message: Message
    before: List[Message]
    after: List[Message]

def dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert dataclass to dictionary with datetime serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    elif hasattr(obj, '__dataclass_fields__'):
        result = {}
        for field_name, field_value in asdict(obj).items():
            if isinstance(field_value, datetime):
                result[field_name] = field_value.isoformat()
            elif isinstance(field_value, list):
                result[field_name] = [dataclass_to_dict(item) for item in field_value]
            else:
                result[field_name] = field_value
        return result
    else:
        return obj

def get_sender_name(sender_jid: str) -> str:
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # First try matching by exact JID
        cursor.execute("""
            SELECT name
            FROM chats
            WHERE jid = ?
            LIMIT 1
        """, (sender_jid,))
        
        result = cursor.fetchone()
        
        # If no result, try looking for the number within JIDs
        if not result:
            # Extract the phone number part if it's a JID
            if '@' in sender_jid:
                phone_part = sender_jid.split('@')[0]
            else:
                phone_part = sender_jid
                
            cursor.execute("""
                SELECT name
                FROM chats
                WHERE jid LIKE ?
                LIMIT 1
            """, (f"%{phone_part}%",))
            
            result = cursor.fetchone()
        
        if result and result[0]:
            return result[0]
        else:
            return sender_jid
        
    except sqlite3.Error as e:
        print(f"Database error while getting sender name: {e}")
        return sender_jid
    finally:
        if 'conn' in locals():
            conn.close()

def format_message(message: Message, show_chat_info: bool = True) -> None:
    """Print a single message with consistent formatting."""
    output = ""
    
    if show_chat_info and message.chat_name:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] Chat: {message.chat_name} "
    else:
        output += f"[{message.timestamp:%Y-%m-%d %H:%M:%S}] "
        
    content_prefix = ""
    if hasattr(message, 'media_type') and message.media_type:
        content_prefix = f"[{message.media_type} - Message ID: {message.id} - Chat JID: {message.chat_jid}] "
    
    try:
        sender_name = get_sender_name(message.sender) if not message.is_from_me else "Me"
        output += f"From: {sender_name}: {content_prefix}{message.content}\n"
    except Exception as e:
        print(f"Error formatting message: {e}")
    return output

def format_messages_list(messages: List[Message], show_chat_info: bool = True) -> None:
    output = ""
    if not messages:
        output += "No messages to display."
        return output
    
    for message in messages:
        output += format_message(message, show_chat_info)
    return output

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
    """Get messages matching the specified criteria with optional context."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Build base query
        query_parts = ["SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type, COALESCE(contacts.name, messages.sender) as sender_name FROM messages"]
        query_parts.append("JOIN chats ON messages.chat_jid = chats.jid")
        query_parts.append("LEFT JOIN contacts ON messages.sender = SUBSTR(contacts.jid, 1, INSTR(contacts.jid, '@') - 1)")
        where_clauses = []
        params = []
        
        # Add filters
        if after:
            try:
                after = datetime.fromisoformat(after)
            except ValueError:
                raise ValueError(f"Invalid date format for 'after': {after}. Please use ISO-8601 format.")
            
            where_clauses.append("messages.timestamp > ?")
            params.append(after)

        if before:
            try:
                before = datetime.fromisoformat(before)
            except ValueError:
                raise ValueError(f"Invalid date format for 'before': {before}. Please use ISO-8601 format.")
            
            where_clauses.append("messages.timestamp < ?")
            params.append(before)

        if sender_phone_number:
            where_clauses.append("messages.sender = ?")
            params.append(sender_phone_number)
            
        if chat_jid:
            where_clauses.append("messages.chat_jid = ?")
            params.append(chat_jid)
            
        if query:
            where_clauses.append("LOWER(messages.content) LIKE LOWER(?)")
            params.append(f"%{query}%")
            
        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))
            
        # Add pagination
        offset = page * limit
        query_parts.append("ORDER BY messages.timestamp DESC")
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        
        cursor.execute(" ".join(query_parts), tuple(params))
        messages = cursor.fetchall()
        
        result = []
        for msg in messages:
            message = Message(
                timestamp=datetime.fromisoformat(msg[0]),
                sender=msg[1],
                chat_name=msg[2],
                content=msg[3],
                is_from_me=msg[4],
                chat_jid=msg[5],
                id=msg[6],
                media_type=msg[7],
                sender_name=msg[8]
            )
            result.append(message)
            
        if include_context and result:
            # Add context for each message
            messages_with_context = []
            for msg in result:
                context = get_message_context(msg.id, context_before, context_after)
                messages_with_context.extend(context.before)
                messages_with_context.append(context.message)
                messages_with_context.extend(context.after)

            return [dataclass_to_dict(msg) for msg in messages_with_context]

        # Return messages without context
        return [dataclass_to_dict(msg) for msg in result]    
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> MessageContext:
    """Get context around a specific message."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        # Get the target message first
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.chat_jid, messages.media_type, COALESCE(contacts.name, messages.sender) as sender_name
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            LEFT JOIN contacts ON messages.sender = SUBSTR(contacts.jid, 1, INSTR(contacts.jid, '@') - 1)
            WHERE messages.id = ?
        """, (message_id,))
        msg_data = cursor.fetchone()

        if not msg_data:
            raise ValueError(f"Message with ID {message_id} not found")

        target_message = Message(
            timestamp=datetime.fromisoformat(msg_data[0]),
            sender=msg_data[1],
            chat_name=msg_data[2],
            content=msg_data[3],
            is_from_me=msg_data[4],
            chat_jid=msg_data[5],
            id=msg_data[6],
            media_type=msg_data[8],
            sender_name=msg_data[9]
        )
        
        # Get messages before
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type, COALESCE(contacts.name, messages.sender) as sender_name
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            LEFT JOIN contacts ON messages.sender = SUBSTR(contacts.jid, 1, INSTR(contacts.jid, '@') - 1)
            WHERE messages.chat_jid = ? AND messages.timestamp < ?
            ORDER BY messages.timestamp DESC
            LIMIT ?
        """, (msg_data[7], msg_data[0], before))

        before_messages = []
        for msg in cursor.fetchall():
            before_messages.append(Message(
                timestamp=datetime.fromisoformat(msg[0]),
                sender=msg[1],
                chat_name=msg[2],
                content=msg[3],
                is_from_me=msg[4],
                chat_jid=msg[5],
                id=msg[6],
                media_type=msg[7],
                sender_name=msg[8]
            ))

        # Get messages after
        cursor.execute("""
            SELECT messages.timestamp, messages.sender, chats.name, messages.content, messages.is_from_me, chats.jid, messages.id, messages.media_type, COALESCE(contacts.name, messages.sender) as sender_name
            FROM messages
            JOIN chats ON messages.chat_jid = chats.jid
            LEFT JOIN contacts ON messages.sender = SUBSTR(contacts.jid, 1, INSTR(contacts.jid, '@') - 1)
            WHERE messages.chat_jid = ? AND messages.timestamp > ?
            ORDER BY messages.timestamp ASC
            LIMIT ?
        """, (msg_data[7], msg_data[0], after))

        after_messages = []
        for msg in cursor.fetchall():
            after_messages.append(Message(
                timestamp=datetime.fromisoformat(msg[0]),
                sender=msg[1],
                chat_name=msg[2],
                content=msg[3],
                is_from_me=msg[4],
                chat_jid=msg[5],
                id=msg[6],
                media_type=msg[7],
                sender_name=msg[8]
            ))
        
        return MessageContext(
            message=target_message,
            before=before_messages,
            after=after_messages
        )
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get chats matching the specified criteria."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        # Build base query
        query_parts = ["""
            SELECT
                chats.jid,
                chats.name,
                chats.last_message_time,
                messages.content as last_message,
                messages.sender as last_sender,
                messages.is_from_me as last_is_from_me,
                chats.parent_group_jid
            FROM chats
        """]

        if include_last_message:
            query_parts.append("""
                LEFT JOIN messages ON chats.jid = messages.chat_jid
                AND chats.last_message_time = messages.timestamp
            """)

        where_clauses = []
        params = []

        if query:
            where_clauses.append("(LOWER(chats.name) LIKE LOWER(?) OR chats.jid LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        # Add sorting
        order_by = "chats.last_message_time DESC" if sort_by == "last_active" else "chats.name"
        query_parts.append(f"ORDER BY {order_by}")

        # Add pagination
        offset = (page ) * limit
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        cursor.execute(" ".join(query_parts), tuple(params))
        chats = cursor.fetchall()

        result = []
        for chat_data in chats:
            chat = Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5],
                parent_group_jid=chat_data[6] if len(chat_data) > 6 else None
            )
            result.append(dataclass_to_dict(chat))

        return result

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search contacts by name or phone number."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        # Split query into characters to support partial matching
        search_pattern = '%' +query + '%'

        cursor.execute("""
            SELECT DISTINCT
                jid,
                name
            FROM chats
            WHERE
                (LOWER(name) LIKE LOWER(?) OR LOWER(jid) LIKE LOWER(?))
                AND jid NOT LIKE '%@g.us'
            ORDER BY name, jid
            LIMIT 50
        """, (search_pattern, search_pattern))

        contacts = cursor.fetchall()

        result = []
        for contact_data in contacts:
            contact = Contact(
                phone_number=contact_data[0].split('@')[0],
                name=contact_data[1],
                jid=contact_data[0]
            )
            result.append(dataclass_to_dict(contact))

        return result

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all chats involving the contact.

    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
            JOIN messages m ON c.jid = m.chat_jid
            WHERE m.sender = ? OR c.jid = ?
            ORDER BY c.last_message_time DESC
            LIMIT ? OFFSET ?
        """, (jid, jid, limit, page * limit))

        chats = cursor.fetchall()

        result = []
        for chat_data in chats:
            chat = Chat(
                jid=chat_data[0],
                name=chat_data[1],
                last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
                last_message=chat_data[3],
                last_sender=chat_data[4],
                last_is_from_me=chat_data[5]
            )
            result.append(dataclass_to_dict(chat))

        return result

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def get_last_interaction(jid: str) -> str:
    """Get most recent message involving the contact."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                m.timestamp,
                m.sender,
                c.name,
                m.content,
                m.is_from_me,
                c.jid,
                m.id,
                m.media_type,
                COALESCE(contacts.name, m.sender) as sender_name
            FROM messages m
            JOIN chats c ON m.chat_jid = c.jid
            LEFT JOIN contacts ON m.sender = SUBSTR(contacts.jid, 1, INSTR(contacts.jid, '@') - 1)
            WHERE m.sender = ? OR c.jid = ?
            ORDER BY m.timestamp DESC
            LIMIT 1
        """, (jid, jid))

        msg_data = cursor.fetchone()

        if not msg_data:
            return None

        message = Message(
            timestamp=datetime.fromisoformat(msg_data[0]),
            sender=msg_data[1],
            chat_name=msg_data[2],
            content=msg_data[3],
            is_from_me=msg_data[4],
            chat_jid=msg_data[5],
            id=msg_data[6],
            media_type=msg_data[7],
            sender_name=msg_data[8]
        )
        
        return format_message(message)
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def get_chat(chat_jid: str, include_last_message: bool = True) -> Optional[Dict[str, Any]]:
    """Get chat metadata by JID."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        query = """
            SELECT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
        """

        if include_last_message:
            query += """
                LEFT JOIN messages m ON c.jid = m.chat_jid
                AND c.last_message_time = m.timestamp
            """

        query += " WHERE c.jid = ?"

        cursor.execute(query, (chat_jid,))
        chat_data = cursor.fetchone()

        if not chat_data:
            return None

        chat = Chat(
            jid=chat_data[0],
            name=chat_data[1],
            last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
            last_message=chat_data[3],
            last_sender=chat_data[4],
            last_is_from_me=chat_data[5]
        )
        return dataclass_to_dict(chat)

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def get_direct_chat_by_contact(sender_phone_number: str) -> Optional[Dict[str, Any]]:
    """Get chat metadata by sender phone number."""
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.jid,
                c.name,
                c.last_message_time,
                m.content as last_message,
                m.sender as last_sender,
                m.is_from_me as last_is_from_me
            FROM chats c
            LEFT JOIN messages m ON c.jid = m.chat_jid
                AND c.last_message_time = m.timestamp
            WHERE c.jid LIKE ? AND c.jid NOT LIKE '%@g.us'
            LIMIT 1
        """, (f"%{sender_phone_number}%",))

        chat_data = cursor.fetchone()

        if not chat_data:
            return None

        chat = Chat(
            jid=chat_data[0],
            name=chat_data[1],
            last_message_time=datetime.fromisoformat(chat_data[2]) if chat_data[2] else None,
            last_message=chat_data[3],
            last_sender=chat_data[4],
            last_is_from_me=chat_data[5]
        )
        return dataclass_to_dict(chat)

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def list_communities(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0
) -> List[Dict[str, Any]]:
    """Get all WhatsApp Communities (chats ending with @newsletter).

    Args:
        query: Optional search term to filter communities by name
        limit: Maximum number of communities to return (default 20)
        page: Page number for pagination (default 0)

    Returns:
        List of community dictionaries with group counts
    """
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        # Build query to get communities
        query_parts = ["""
            SELECT
                c.jid,
                c.name,
                COUNT(DISTINCT groups.jid) as group_count
            FROM chats c
            LEFT JOIN chats groups ON groups.parent_group_jid = c.jid
            WHERE c.jid LIKE '%@newsletter'
        """]

        params = []

        if query:
            query_parts.append("AND LOWER(c.name) LIKE LOWER(?)")
            params.append(f"%{query}%")

        query_parts.append("GROUP BY c.jid, c.name")
        query_parts.append("ORDER BY c.name")

        # Add pagination
        offset = page * limit
        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        cursor.execute(" ".join(query_parts), tuple(params))
        communities = cursor.fetchall()

        result = []
        for comm_data in communities:
            community = Community(
                jid=comm_data[0],
                name=comm_data[1],
                group_count=comm_data[2]
            )
            result.append(dataclass_to_dict(community))

        return result

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def get_community_groups(
    community_jid: str,
    limit: int = 100,
    page: int = 0
) -> List[Dict[str, Any]]:
    """Get all groups belonging to a specific community.

    Args:
        community_jid: The JID of the community
        limit: Maximum number of groups to return (default 100)
        page: Page number for pagination (default 0)

    Returns:
        List of chat dictionaries for groups in the community
    """
    try:
        conn = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = conn.cursor()

        # Get all groups with this parent_group_jid
        query = """
            SELECT
                jid,
                name,
                last_message_time,
                parent_group_jid
            FROM chats
            WHERE parent_group_jid = ?
            ORDER BY name
            LIMIT ? OFFSET ?
        """

        offset = page * limit
        cursor.execute(query, (community_jid, limit, offset))
        groups = cursor.fetchall()

        result = []
        for group_data in groups:
            chat = Chat(
                jid=group_data[0],
                name=group_data[1],
                last_message_time=datetime.fromisoformat(group_data[2]) if group_data[2] else None,
                parent_group_jid=group_data[3]
            )
            result.append(dataclass_to_dict(chat))

        return result

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def sync_chat_history(chat_jid: str, count: int = 50) -> Tuple[bool, str]:
    """Sync message history for a specific chat from WhatsApp.

    Args:
        chat_jid: The JID of the chat to sync
        count: Number of messages to sync (default 50)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/sync_chat_history"
        payload = {
            "chat_jid": chat_jid,
            "count": count
        }

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


# =============================================================================
# Community API Functions (Go REST API)
# =============================================================================

def list_communities_go_api(
    query: Optional[str] = None,
    limit: int = 20
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """List all WhatsApp communities via Go REST API.

    Args:
        query: Optional search term to filter communities by name
        limit: Maximum number of communities to return (default 20)

    Returns:
        Tuple of (success: bool, message: str, communities: list)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/communities/list"
        params = {"limit": limit}
        if query:
            params["query"] = query

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Communities retrieved"),
                result.get("communities", [])
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", []

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def get_community_metadata_go_api(community_jid: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Get community metadata via Go REST API.

    Args:
        community_jid: The JID of the community

    Returns:
        Tuple of (success: bool, message: str, community: dict or None)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/communities/{community_jid}"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Community metadata retrieved"),
                result.get("community")
            )
        elif response.status_code == 404:
            return False, "Community not found", None
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def get_community_groups_go_api(
    community_jid: str,
    limit: int = 100
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Get groups in a community via Go REST API.

    Args:
        community_jid: The JID of the community
        limit: Maximum number of groups to return (default 100)

    Returns:
        Tuple of (success: bool, message: str, groups: list)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/communities/{community_jid}/groups"
        params = {"limit": limit}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Groups retrieved"),
                result.get("groups", [])
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", []

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def mark_community_as_read_go_api(community_jid: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Mark all messages in all groups of a community as read via Go REST API.

    This uses the Go backend's mark-read endpoint which calls the WhatsApp API
    directly to mark messages as read (not just in the database).

    Args:
        community_jid: The JID of the community

    Returns:
        Tuple of (success: bool, message: str, details: dict with per-group results)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/communities/{community_jid}/mark-read"

        response = requests.post(url, timeout=60)  # Longer timeout for multi-group operation

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Community marked as read"),
                result.get("group_results", {})
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", {}

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", {}
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


# =============================================================================
# Status API Functions (Baileys REST API)
# =============================================================================

def post_status_baileys_api(
    text: Optional[str] = None,
    media_path: Optional[str] = None,
    background_color: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Post a WhatsApp Status update via Baileys REST API.

    Args:
        text: Optional text content for the status
        media_path: Optional path to media file (image/video)
        background_color: Optional background color for text status (hex format)

    Returns:
        Tuple of (success: bool, message: str, result: dict with status_id and timestamp)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/status/post"
        payload = {}

        if text:
            payload["text"] = text
        if media_path:
            payload["media_path"] = media_path
        if background_color:
            payload["background_color"] = background_color

        if not text and not media_path:
            return False, "Either text or media_path must be provided", None

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Status posted"),
                result
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def list_status_baileys_api(
    limit: int = 50
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Get status updates from contacts via Baileys REST API.

    Args:
        limit: Maximum number of statuses to return (default 50)

    Returns:
        Tuple of (success: bool, message: str, statuses: list)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/status/list"
        params = {"limit": limit}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Statuses retrieved"),
                result.get("statuses", [])
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", []

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def view_status_baileys_api(
    status_id: str,
    owner_jid: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Mark a WhatsApp Status as viewed via Baileys REST API.

    Args:
        status_id: The message ID of the status
        owner_jid: The JID of the status owner

    Returns:
        Tuple of (success: bool, message: str, result: dict with confirmation)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/status/{status_id}/view"
        payload = {"owner_jid": owner_jid}

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Status viewed"),
                result
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def get_status_privacy_baileys_api() -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Get status privacy settings via Baileys REST API.

    Returns:
        Tuple of (success: bool, message: str, privacy: dict with settings)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/status/privacy"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Privacy settings retrieved"),
                result.get("privacy")
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


# =============================================================================
# Poll API Functions (Baileys REST API)
# =============================================================================

def create_poll_v2_baileys_api(
    chat_jid: str,
    name: str,
    options: List[str]
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Create a single-choice poll via Baileys REST API.

    Args:
        chat_jid: The JID of the chat to send the poll to
        name: The poll question
        options: List of poll options (2-12 items)

    Returns:
        Tuple of (success: bool, message: str, result: dict with message_id and metadata)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/polls/create-v2"
        payload = {
            "chat_jid": chat_jid,
            "name": name,
            "options": options
        }

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Poll created"),
                result
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def create_poll_v3_baileys_api(
    chat_jid: str,
    name: str,
    options: List[str],
    allow_multiple: bool = True,
    max_selections: Optional[int] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Create a multiple-choice poll via Baileys REST API.

    Args:
        chat_jid: The JID of the chat to send the poll to
        name: The poll question
        options: List of poll options (2-12 items)
        allow_multiple: Whether to allow multiple selections (default True)
        max_selections: Maximum number of selections allowed (default None = all)

    Returns:
        Tuple of (success: bool, message: str, result: dict with message_id and metadata)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/polls/create-v3"
        payload = {
            "chat_jid": chat_jid,
            "name": name,
            "options": options,
            "allow_multiple": allow_multiple
        }

        if max_selections is not None:
            payload["max_selections"] = max_selections

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Poll created"),
                result
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def vote_poll_baileys_api(
    chat_jid: str,
    message_id: str,
    option_indices: List[int]
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Vote on a poll via Baileys REST API.

    Args:
        chat_jid: The JID of the chat containing the poll
        message_id: The message ID of the poll
        option_indices: List of option indices to vote for (0-based)

    Returns:
        Tuple of (success: bool, message: str, result: dict with vote confirmation)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/polls/{message_id}/vote"
        payload = {
            "chat_jid": chat_jid,
            "option_indices": option_indices
        }

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Vote submitted"),
                result
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def get_poll_results_baileys_api(
    chat_jid: str,
    message_id: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Get poll results via Baileys REST API.

    Args:
        chat_jid: The JID of the chat containing the poll
        message_id: The message ID of the poll

    Returns:
        Tuple of (success: bool, message: str, results: dict with poll results)
    """
    try:
        url = f"{BAILEYS_API_BASE_URL}/polls/{message_id}/results"
        params = {"chat_jid": chat_jid}

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Poll results retrieved"),
                result
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


# =============================================================================
# Group API Functions (Go REST API)
# =============================================================================

def create_group_go_api(
    name: str,
    participants: List[str]
) -> Tuple[bool, str, Optional[str]]:
    """Create a new WhatsApp group via Go REST API.

    Args:
        name: The name of the group
        participants: List of participant phone numbers or JIDs

    Returns:
        Tuple of (success: bool, message: str, group_jid: str or None)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/create"
        payload = {
            "name": name,
            "participants": participants
        }

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Group created"),
                result.get("group_jid")
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def update_group_metadata_go_api(
    group_jid: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    picture: Optional[str] = None
) -> Tuple[bool, str]:
    """Update WhatsApp group metadata via Go REST API.

    Args:
        group_jid: The JID of the group
        name: Optional new group name
        description: Optional new group description
        picture: Optional path to new group picture

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/metadata"
        payload = {}

        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if picture:
            payload["picture"] = picture

        if not payload:
            return False, "At least one metadata field must be provided"

        response = requests.put(url, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Metadata updated")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def add_group_participants_go_api(
    group_jid: str,
    participants: List[str]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Add participants to a WhatsApp group via Go REST API.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers or JIDs to add

    Returns:
        Tuple of (success: bool, message: str, results: dict with per-participant status)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/participants/add"
        payload = {"participants": participants}

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Participants added"),
                result.get("results", {})
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", {}

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", {}
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def remove_group_participants_go_api(
    group_jid: str,
    participants: List[str]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Remove participants from a WhatsApp group via Go REST API.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers or JIDs to remove

    Returns:
        Tuple of (success: bool, message: str, results: dict with per-participant status)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/participants/remove"
        payload = {"participants": participants}

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Participants removed"),
                result.get("results", {})
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", {}

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", {}
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def promote_group_participants_go_api(
    group_jid: str,
    participants: List[str]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Promote participants to admins in a WhatsApp group via Go REST API.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers or JIDs to promote

    Returns:
        Tuple of (success: bool, message: str, results: dict with per-participant status)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/participants/promote"
        payload = {"participants": participants}

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Participants promoted"),
                result.get("results", {})
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", {}

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", {}
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def demote_group_participants_go_api(
    group_jid: str,
    participants: List[str]
) -> Tuple[bool, str, Dict[str, Any]]:
    """Demote participants from admins to members in a WhatsApp group via Go REST API.

    Args:
        group_jid: The JID of the group
        participants: List of participant phone numbers or JIDs to demote

    Returns:
        Tuple of (success: bool, message: str, results: dict with per-participant status)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/participants/demote"
        payload = {"participants": participants}

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Participants demoted"),
                result.get("results", {})
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", {}

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", {}
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", {}
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", {}


def get_group_participants_go_api(
    group_jid: str
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Get all participants in a WhatsApp group via Go REST API.

    Args:
        group_jid: The JID of the group

    Returns:
        Tuple of (success: bool, message: str, participants: list of participant dicts)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/participants"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Participants retrieved"),
                result.get("participants", [])
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", []

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", []
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", []
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", []


def get_group_invite_link_go_api(
    group_jid: str
) -> Tuple[bool, str, Optional[str]]:
    """Get the invite link for a WhatsApp group via Go REST API.

    Args:
        group_jid: The JID of the group

    Returns:
        Tuple of (success: bool, message: str, invite_link: str or None)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/invite"

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Invite link retrieved"),
                result.get("invite_link")
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def revoke_group_invite_link_go_api(
    group_jid: str
) -> Tuple[bool, str, Optional[str]]:
    """Revoke and regenerate the invite link for a WhatsApp group via Go REST API.

    Args:
        group_jid: The JID of the group

    Returns:
        Tuple of (success: bool, message: str, new_invite_link: str or None)
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/groups/{group_jid}/invite/revoke"

        response = requests.post(url, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return (
                result.get("success", False),
                result.get("message", "Invite link revoked"),
                result.get("invite_link")
            )
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}", None

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}", None
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}", None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None


def mark_community_as_read(community_jid: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Mark all messages in all groups of a community as read.

    NOTE: This function only marks messages that are already in the local database as read.
    To ensure messages are in the database, you should first sync history using the general
    history sync endpoint (/api/sync_history) and wait for it to complete.

    Args:
        community_jid: The JID of the community

    Returns:
        Tuple of (success: bool, message: str, details: dict with per-group results)
    """
    try:
        # Get all groups in the community
        groups = get_community_groups(community_jid, limit=1000)

        if not groups:
            return False, f"No groups found for community {community_jid}", {}

        results = {}
        success_count = 0
        fail_count = 0
        skipped_count = 0

        for group in groups:
            group_jid = group['jid']
            group_name = group.get('name', 'Unknown')

            print(f"Processing {group_name}...")

            # Get all messages in this group from the database
            conn = sqlite3.connect(MESSAGES_DB_PATH)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, sender
                FROM messages
                WHERE chat_jid = ? AND is_from_me = 0
                ORDER BY timestamp DESC
                LIMIT 1000
            """, (group_jid,))

            messages = cursor.fetchall()
            conn.close()

            if not messages:
                results[group_name] = {"success": True, "message": "No messages in database to mark", "count": 0, "skipped": True}
                skipped_count += 1
                continue

            # Extract message IDs and sender (for group messages, we need the sender)
            message_ids = [msg[0] for msg in messages]
            # For group chats, we might need a sender JID, use the first message's sender
            sender_jid = messages[0][1] if messages else None

            # Mark as read
            success, message = mark_as_read(group_jid, message_ids, sender_jid)

            results[group_name] = {
                "success": success,
                "message": message,
                "count": len(message_ids),
                "skipped": False
            }

            if success:
                success_count += 1
            else:
                fail_count += 1

        overall_message = f"Marked {success_count} groups as read"
        if fail_count > 0:
            overall_message += f", {fail_count} groups failed"
        if skipped_count > 0:
            overall_message += f", {skipped_count} groups skipped (no messages in database)"

        return success_count > 0, overall_message, results

    except Exception as e:
        return False, f"Error marking community as read: {str(e)}", {}


def send_message(recipient: str, message: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "message": message,
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_file(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        if not media_path:
            return False, "Media path must be provided"
        
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def send_audio_message(recipient: str, media_path: str) -> Tuple[bool, str]:
    try:
        # Validate input
        if not recipient:
            return False, "Recipient must be provided"
        
        if not media_path:
            return False, "Media path must be provided"
        
        if not os.path.isfile(media_path):
            return False, f"Media file not found: {media_path}"

        if not media_path.endswith(".ogg"):
            try:
                media_path = audio.convert_to_opus_ogg_temp(media_path)
            except Exception as e:
                return False, f"Error converting file to opus ogg. You likely need to install ffmpeg: {str(e)}"
        
        url = f"{WHATSAPP_API_BASE_URL}/send"
        payload = {
            "recipient": recipient,
            "media_path": media_path
        }
        
        response = requests.post(url, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"
            
    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def download_media(message_id: str, chat_jid: str) -> Optional[str]:
    """Download media from a message and return the local file path.

    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message

    Returns:
        The local file path if download was successful, None otherwise
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/download"
        payload = {
            "message_id": message_id,
            "chat_jid": chat_jid
        }

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                path = result.get("path")
                print(f"Media downloaded successfully: {path}")
                return path
            else:
                print(f"Download failed: {result.get('message', 'Unknown error')}")
                return None
        else:
            print(f"Error: HTTP {response.status_code} - {response.text}")
            return None

    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except json.JSONDecodeError:
        print(f"Error parsing response: {response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def mark_as_read(chat_jid: str, message_ids: List[str], sender: Optional[str] = None) -> Tuple[bool, str]:
    """Mark messages as read in a WhatsApp chat.

    Args:
        chat_jid: The JID of the chat containing the messages
        message_ids: List of message IDs to mark as read
        sender: Optional sender JID (required for group chats)

    Returns:
        A tuple of (success: bool, message: str)
    """
    try:
        # Validate input
        if not chat_jid:
            return False, "Chat JID must be provided"

        if not message_ids or len(message_ids) == 0:
            return False, "At least one message ID must be provided"

        url = f"{WHATSAPP_API_BASE_URL}/mark_read"
        payload = {
            "chat_jid": chat_jid,
            "message_ids": message_ids,
        }

        if sender:
            payload["sender"] = sender

        response = requests.post(url, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            return result.get("success", False), result.get("message", "Unknown response")
        else:
            return False, f"Error: HTTP {response.status_code} - {response.text}"

    except requests.RequestException as e:
        return False, f"Request error: {str(e)}"
    except json.JSONDecodeError:
        return False, f"Error parsing response: {response.text}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
