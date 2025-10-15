"""
Test Data Schemas and Sample Data Generators

Defines the structure and constraints for test data used across all test types.
These schemas ensure consistency and validity of test data.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class MessageType(Enum):
    """Message content types."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACT = "contact"


class ChatType(Enum):
    """Chat types."""
    DIRECT = "direct"
    GROUP = "group"
    COMMUNITY = "community"
    NEWSLETTER = "newsletter"


class BackendHealthStatus(Enum):
    """Backend health statuses."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNREACHABLE = "unreachable"


class ReadStatus(Enum):
    """Message read status."""
    UNREAD = "unread"
    READ = "read"
    PENDING = "pending"


# Test constants
TEST_TIMESTAMP_BASE = 1728745200  # 2025-10-12 14:00:00 UTC (deterministic)
TEST_COMMUNITY_JID = "120363143634035041@g.us"
TEST_GROUP_JID_1 = "120363281234567890@g.us"
TEST_GROUP_JID_2 = "120363289876543210@g.us"
TEST_DIRECT_CHAT_JID = "1234567890@s.whatsapp.net"


# ============================================================================
# MESSAGE SCHEMAS
# ============================================================================

@dataclass
class TestMessage:
    """
    Schema for test message data.

    Contract:
        - message_id MUST be unique within test
        - chat_jid MUST be valid WhatsApp JID format
        - timestamp MUST be deterministic (based on TEST_TIMESTAMP_BASE)
        - content MUST NOT be empty for text messages
        - media_path MUST be valid path if media_type is not None
    """
    message_id: str
    chat_jid: str
    sender: str
    content: str
    timestamp: int
    is_from_me: bool
    read_status: ReadStatus
    message_type: MessageType = MessageType.TEXT
    media_path: Optional[str] = None
    quoted_message_id: Optional[str] = None
    reactions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.message_id,
            "chat_jid": self.chat_jid,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "is_from_me": self.is_from_me,
            "read_status": self.read_status.value,
            "message_type": self.message_type.value,
            "media_path": self.media_path,
            "quoted_message_id": self.quoted_message_id,
            "reactions": self.reactions
        }

    @classmethod
    def create_text_message(cls, msg_id: int, chat_jid: str, content: str,
                           offset_seconds: int = 0, is_read: bool = False) -> "TestMessage":
        """
        Factory method for creating text messages.

        Args:
            msg_id: Unique message number (used to generate message_id)
            chat_jid: Chat JID
            content: Message text content
            offset_seconds: Seconds to add to TEST_TIMESTAMP_BASE
            is_read: Whether message has been read

        Returns:
            TestMessage instance
        """
        return cls(
            message_id=f"msg-{msg_id:05d}",
            chat_jid=chat_jid,
            sender=f"{msg_id % 10}1234567890@s.whatsapp.net",
            content=content,
            timestamp=TEST_TIMESTAMP_BASE + offset_seconds,
            is_from_me=msg_id % 3 == 0,  # Every 3rd message is from user
            read_status=ReadStatus.READ if is_read else ReadStatus.UNREAD,
            message_type=MessageType.TEXT
        )

    @classmethod
    def create_media_message(cls, msg_id: int, chat_jid: str, media_type: MessageType,
                            media_path: str, offset_seconds: int = 0) -> "TestMessage":
        """
        Factory method for creating media messages.

        Args:
            msg_id: Unique message number
            chat_jid: Chat JID
            media_type: Type of media (IMAGE, VIDEO, AUDIO, DOCUMENT)
            media_path: Path to media file
            offset_seconds: Seconds to add to TEST_TIMESTAMP_BASE

        Returns:
            TestMessage instance
        """
        return cls(
            message_id=f"msg-media-{msg_id:05d}",
            chat_jid=chat_jid,
            sender=f"{msg_id % 10}1234567890@s.whatsapp.net",
            content=f"[{media_type.value}]",
            timestamp=TEST_TIMESTAMP_BASE + offset_seconds,
            is_from_me=False,
            read_status=ReadStatus.UNREAD,
            message_type=media_type,
            media_path=media_path
        )


# ============================================================================
# CHAT SCHEMAS
# ============================================================================

@dataclass
class TestChat:
    """
    Schema for test chat data.

    Contract:
        - jid MUST be unique
        - name MUST NOT be empty
        - For GROUP chats, participants MUST have at least 2 members
        - For DIRECT chats, participants MUST be empty
        - unread_count MUST be >= 0
    """
    jid: str
    name: str
    chat_type: ChatType
    unread_count: int
    last_message_timestamp: int
    is_archived: bool = False
    is_pinned: bool = False
    is_muted: bool = False
    participants: List[str] = field(default_factory=list)
    parent_community_jid: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "jid": self.jid,
            "name": self.name,
            "chat_type": self.chat_type.value,
            "unread_count": self.unread_count,
            "last_message_timestamp": self.last_message_timestamp,
            "is_archived": self.is_archived,
            "is_pinned": self.is_pinned,
            "is_muted": self.is_muted,
            "participants": self.participants,
            "parent_community_jid": self.parent_community_jid
        }

    @classmethod
    def create_direct_chat(cls, chat_id: int, unread_count: int = 0) -> "TestChat":
        """Factory for direct chats."""
        return cls(
            jid=f"{chat_id}1234567890@s.whatsapp.net",
            name=f"Test Contact {chat_id}",
            chat_type=ChatType.DIRECT,
            unread_count=unread_count,
            last_message_timestamp=TEST_TIMESTAMP_BASE + chat_id * 100,
            participants=[]
        )

    @classmethod
    def create_group_chat(cls, group_id: int, participant_count: int = 5,
                         unread_count: int = 0, parent_community: Optional[str] = None) -> "TestChat":
        """Factory for group chats."""
        return cls(
            jid=f"12036328{group_id:07d}@g.us",
            name=f"Test Group {group_id}",
            chat_type=ChatType.GROUP,
            unread_count=unread_count,
            last_message_timestamp=TEST_TIMESTAMP_BASE + group_id * 200,
            participants=[f"{i}1234567890@s.whatsapp.net" for i in range(participant_count)],
            parent_community_jid=parent_community
        )


# ============================================================================
# CONTACT SCHEMAS
# ============================================================================

@dataclass
class TestContact:
    """
    Schema for test contact data.

    Contract:
        - jid MUST be valid WhatsApp JID
        - phone MUST be E.164 format (optional)
        - name MUST NOT be empty
    """
    jid: str
    name: str
    phone: Optional[str] = None
    is_business: bool = False
    is_blocked: bool = False
    profile_picture_url: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "jid": self.jid,
            "name": self.name,
            "phone": self.phone,
            "is_business": self.is_business,
            "is_blocked": self.is_blocked,
            "profile_picture_url": self.profile_picture_url
        }

    @classmethod
    def create_contact(cls, contact_id: int) -> "TestContact":
        """Factory for contacts."""
        return cls(
            jid=f"{contact_id}1234567890@s.whatsapp.net",
            name=f"Test Contact {contact_id}",
            phone=f"+1234567{contact_id:04d}",
            is_business=contact_id % 5 == 0  # Every 5th contact is business
        )


# ============================================================================
# COMMUNITY SCHEMAS
# ============================================================================

@dataclass
class TestCommunity:
    """
    Schema for test community data.

    Contract:
        - jid MUST be community JID format (*@g.us)
        - groups MUST have at least 1 group
        - Each group MUST be valid TestChat with chat_type=GROUP
    """
    jid: str
    name: str
    groups: List[TestChat] = field(default_factory=list)
    total_unread_messages: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "jid": self.jid,
            "name": self.name,
            "groups": [g.to_dict() for g in self.groups],
            "total_unread_messages": self.total_unread_messages
        }

    @classmethod
    def create_test_community(cls, community_id: int, num_groups: int = 2,
                             messages_per_group: int = 50) -> "TestCommunity":
        """
        Factory for test communities.

        Args:
            community_id: Unique community identifier
            num_groups: Number of groups in community
            messages_per_group: Unread messages per group

        Returns:
            TestCommunity instance with groups
        """
        groups = [
            TestChat.create_group_chat(
                group_id=community_id * 100 + i,
                participant_count=10,
                unread_count=messages_per_group,
                parent_community=f"12036314{community_id:07d}@g.us"
            )
            for i in range(num_groups)
        ]

        return cls(
            jid=f"12036314{community_id:07d}@g.us",
            name=f"Test Community {community_id}",
            groups=groups,
            total_unread_messages=num_groups * messages_per_group
        )


# ============================================================================
# HEALTH CHECK SCHEMAS
# ============================================================================

@dataclass
class TestHealthResponse:
    """
    Schema for backend health check responses.

    Contract:
        - status MUST be valid BackendHealthStatus
        - uptime_seconds MUST be >= 0
        - requests_handled MUST be >= 0
        - If status is UNHEALTHY, last_error SHOULD be set
    """
    status: BackendHealthStatus
    uptime_seconds: int
    requests_handled: int
    active_connections: int
    last_error: Optional[str] = None
    backend_version: str = "1.0.0-test"

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "uptime_seconds": self.uptime_seconds,
            "requests_handled": self.requests_handled,
            "active_connections": self.active_connections,
            "last_error": self.last_error,
            "backend_version": self.backend_version
        }

    @classmethod
    def create_healthy(cls, backend_name: str = "test") -> "TestHealthResponse":
        """Factory for healthy backend."""
        return cls(
            status=BackendHealthStatus.HEALTHY,
            uptime_seconds=3600,
            requests_handled=1250,
            active_connections=5,
            last_error=None,
            backend_version=f"{backend_name}-1.0.0"
        )

    @classmethod
    def create_unhealthy(cls, error_message: str) -> "TestHealthResponse":
        """Factory for unhealthy backend."""
        return cls(
            status=BackendHealthStatus.UNHEALTHY,
            uptime_seconds=120,
            requests_handled=50,
            active_connections=0,
            last_error=error_message
        )

    @classmethod
    def create_degraded(cls) -> "TestHealthResponse":
        """Factory for degraded backend."""
        return cls(
            status=BackendHealthStatus.DEGRADED,
            uptime_seconds=7200,
            requests_handled=5000,
            active_connections=15,
            last_error="High latency detected"
        )


# ============================================================================
# SYNC CHECKPOINT SCHEMAS
# ============================================================================

@dataclass
class TestSyncCheckpoint:
    """
    Schema for sync checkpoint data.

    Contract:
        - chat_jid MUST be valid
        - messages_synced_count MUST be >= 0
        - If sync_in_progress=True, last_sync_error SHOULD be None
    """
    chat_jid: str
    last_synced_message_id: Optional[str]
    last_synced_timestamp: int
    messages_synced_count: int
    sync_in_progress: bool = False
    last_sync_error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "chat_jid": self.chat_jid,
            "last_synced_message_id": self.last_synced_message_id,
            "last_synced_timestamp": self.last_synced_timestamp,
            "messages_synced_count": self.messages_synced_count,
            "sync_in_progress": self.sync_in_progress,
            "last_sync_error": self.last_sync_error
        }

    @classmethod
    def create_completed_sync(cls, chat_jid: str, message_count: int) -> "TestSyncCheckpoint":
        """Factory for completed sync."""
        return cls(
            chat_jid=chat_jid,
            last_synced_message_id=f"msg-{message_count:05d}",
            last_synced_timestamp=TEST_TIMESTAMP_BASE + message_count,
            messages_synced_count=message_count,
            sync_in_progress=False,
            last_sync_error=None
        )


# ============================================================================
# SAMPLE DATA GENERATORS
# ============================================================================

class TestDataGenerator:
    """
    Generates deterministic test data for various test scenarios.

    All methods produce consistent, reproducible data based on fixed seeds
    and constants to ensure test determinism.
    """

    @staticmethod
    def generate_message_batch(chat_jid: str, count: int = 10,
                               start_offset: int = 0, read_ratio: float = 0.3) -> List[TestMessage]:
        """
        Generate batch of test messages.

        Args:
            chat_jid: Chat JID for messages
            count: Number of messages to generate
            start_offset: Starting offset in seconds from TEST_TIMESTAMP_BASE
            read_ratio: Ratio of messages that are read (0.0-1.0)

        Returns:
            List of TestMessage instances
        """
        messages = []
        for i in range(count):
            is_read = (i / count) < read_ratio
            messages.append(
                TestMessage.create_text_message(
                    msg_id=start_offset + i,
                    chat_jid=chat_jid,
                    content=f"Test message {i+1} of {count}",
                    offset_seconds=i * 60,  # 1 minute apart
                    is_read=is_read
                )
            )
        return messages

    @staticmethod
    def generate_mixed_media_messages(chat_jid: str, count: int = 10) -> List[TestMessage]:
        """
        Generate messages with mix of text and media types.

        Args:
            chat_jid: Chat JID
            count: Total messages (will be distributed across types)

        Returns:
            List of TestMessage instances (text + media)
        """
        messages = []
        media_types = [MessageType.IMAGE, MessageType.VIDEO, MessageType.AUDIO, MessageType.DOCUMENT]

        for i in range(count):
            if i % 4 == 0:  # Every 4th message is media
                media_type = media_types[i % len(media_types)]
                messages.append(
                    TestMessage.create_media_message(
                        msg_id=i,
                        chat_jid=chat_jid,
                        media_type=media_type,
                        media_path=f"/test/media/{media_type.value}/{i}.bin",
                        offset_seconds=i * 120
                    )
                )
            else:
                messages.append(
                    TestMessage.create_text_message(
                        msg_id=i,
                        chat_jid=chat_jid,
                        content=f"Message {i}",
                        offset_seconds=i * 120
                    )
                )
        return messages

    @staticmethod
    def generate_chat_list(num_direct: int = 3, num_groups: int = 2) -> List[TestChat]:
        """
        Generate list of test chats.

        Args:
            num_direct: Number of direct chats
            num_groups: Number of group chats

        Returns:
            List of TestChat instances
        """
        chats = []

        # Direct chats
        for i in range(num_direct):
            chats.append(TestChat.create_direct_chat(chat_id=i, unread_count=i * 2))

        # Group chats
        for i in range(num_groups):
            chats.append(TestChat.create_group_chat(
                group_id=i,
                participant_count=5 + i * 2,
                unread_count=i * 10
            ))

        return chats

    @staticmethod
    def generate_community_with_messages(num_groups: int = 2,
                                        messages_per_group: int = 50) -> tuple[TestCommunity, List[TestMessage]]:
        """
        Generate test community with associated messages.

        Args:
            num_groups: Number of groups in community
            messages_per_group: Messages per group

        Returns:
            Tuple of (TestCommunity, List[TestMessage])
        """
        community = TestCommunity.create_test_community(
            community_id=1,
            num_groups=num_groups,
            messages_per_group=messages_per_group
        )

        all_messages = []
        for group in community.groups:
            messages = TestDataGenerator.generate_message_batch(
                chat_jid=group.jid,
                count=messages_per_group,
                read_ratio=0.0  # All unread initially
            )
            all_messages.extend(messages)

        return community, all_messages


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_message_schema(message_dict: Dict) -> bool:
    """
    Validate that message dictionary conforms to schema.

    Args:
        message_dict: Message data to validate

    Returns:
        True if valid

    Raises:
        ValueError: If schema validation fails
    """
    required_fields = ["id", "chat_jid", "sender", "content", "timestamp",
                      "is_from_me", "read_status", "message_type"]

    for field in required_fields:
        if field not in message_dict:
            raise ValueError(f"Missing required field: {field}")

    if not message_dict["id"]:
        raise ValueError("message_id cannot be empty")

    if not isinstance(message_dict["timestamp"], int):
        raise ValueError("timestamp must be integer")

    return True


def validate_chat_schema(chat_dict: Dict) -> bool:
    """Validate chat dictionary conforms to schema."""
    required_fields = ["jid", "name", "chat_type", "unread_count"]

    for field in required_fields:
        if field not in chat_dict:
            raise ValueError(f"Missing required field: {field}")

    if chat_dict["unread_count"] < 0:
        raise ValueError("unread_count cannot be negative")

    return True


def validate_health_response_schema(health_dict: Dict) -> bool:
    """Validate health response conforms to schema."""
    required_fields = ["status", "uptime_seconds", "requests_handled", "active_connections"]

    for field in required_fields:
        if field not in health_dict:
            raise ValueError(f"Missing required field: {field}")

    valid_statuses = ["healthy", "degraded", "unhealthy", "unreachable"]
    if health_dict["status"] not in valid_statuses:
        raise ValueError(f"Invalid status: {health_dict['status']}")

    return True
