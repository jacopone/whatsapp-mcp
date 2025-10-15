"""Shared pytest fixtures for all test suites.

These fixtures are available to unit, integration, and e2e tests.
"""

import sqlite3

import pytest

# Test constants
TEST_TIMESTAMP_BASE = 1728745200  # 2025-10-12 14:00:00 UTC (deterministic)


@pytest.fixture
def sample_messages() -> list[dict]:
    """Provides deterministic test message data.

    Returns 10+ messages with mixed read/unread status for testing.
    """
    messages = []

    # 5 unread messages
    for i in range(5):
        messages.append({
            "id": f"msg-{i:05d}",
            "chat_jid": "1234567890@s.whatsapp.net",
            "sender": f"{i}9876543210@s.whatsapp.net",
            "content": f"Test message {i}",
            "timestamp": TEST_TIMESTAMP_BASE + i * 60,
            "is_from_me": i % 3 == 0,
            "read_status": "unread",
            "message_type": "text",
            "media_path": None
        })

    # 5 read messages
    for i in range(5, 10):
        messages.append({
            "id": f"msg-{i:05d}",
            "chat_jid": "120363281234567890@g.us",  # Group chat
            "sender": f"{i}9876543210@s.whatsapp.net",
            "content": f"Test message {i}",
            "timestamp": TEST_TIMESTAMP_BASE + i * 60,
            "is_from_me": False,
            "read_status": "read",
            "message_type": "text",
            "media_path": None
        })

    # 1 media message
    messages.append({
        "id": "msg-media-00001",
        "chat_jid": "1234567890@s.whatsapp.net",
        "sender": "9876543210@s.whatsapp.net",
        "content": "[image]",
        "timestamp": TEST_TIMESTAMP_BASE + 600,
        "is_from_me": False,
        "read_status": "unread",
        "message_type": "image",
        "media_path": "/test/media/image001.jpg"
    })

    return messages


@pytest.fixture
def sample_chats() -> list[dict]:
    """Provides deterministic test chat data.

    Returns 3 direct chats and 2 group chats.
    """
    chats = []

    # 3 direct chats
    for i in range(3):
        chats.append({
            "jid": f"{i}1234567890@s.whatsapp.net",
            "name": f"Test Contact {i}",
            "is_group": False,
            "unread_count": i * 2,
            "last_message_timestamp": TEST_TIMESTAMP_BASE + i * 100,
            "participants": None
        })

    # 2 group chats
    for i in range(2):
        chats.append({
            "jid": f"12036328{i:07d}@g.us",
            "name": f"Test Group {i}",
            "is_group": True,
            "unread_count": i * 10,
            "last_message_timestamp": TEST_TIMESTAMP_BASE + (i + 3) * 100,
            "participants": [
                f"{j}1234567890@s.whatsapp.net" for j in range(5)
            ]
        })

    return chats


@pytest.fixture
def sample_health_response() -> dict:
    """Provides sample health check response data.

    Returns healthy backend health response.
    """
    return {
        "status": "healthy",
        "uptime_seconds": 3600,
        "requests_handled": 1250,
        "active_connections": 5,
        "last_error": None,
        "backend_version": "1.0.0-test"
    }


@pytest.fixture
def test_database():
    """Provides in-memory SQLite database for testing.

    Yields database connection with automatic cleanup.
    """
    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Initialize schema (minimal for testing)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            chat_jid TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT,
            timestamp INTEGER NOT NULL,
            is_from_me INTEGER DEFAULT 0,
            read_status TEXT DEFAULT 'unread',
            message_type TEXT DEFAULT 'text',
            media_path TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            jid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            is_group INTEGER DEFAULT 0,
            unread_count INTEGER DEFAULT 0,
            last_message_timestamp INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_checkpoints (
            chat_jid TEXT PRIMARY KEY,
            last_synced_message_id TEXT,
            last_synced_timestamp INTEGER,
            messages_synced_count INTEGER DEFAULT 0,
            sync_in_progress INTEGER DEFAULT 0,
            last_sync_error TEXT
        )
    """)

    conn.commit()

    # Yield connection for test use
    yield conn

    # Cleanup
    conn.close()
