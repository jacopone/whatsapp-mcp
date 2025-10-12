"""
Integration test fixtures for testing with real backends.

These fixtures use pytest-docker to manage Docker containers
for Go and Baileys bridges during integration testing.
"""

import pytest
import requests
import time
import os
from typing import Dict, List


@pytest.fixture(scope="session")
def docker_compose_file():
    """
    Provides path to docker-compose.yml for integration tests.
    """
    return os.path.join(os.path.dirname(__file__), "docker-compose.yml")


@pytest.fixture(scope="session")
def docker_services(docker_compose_file):
    """
    Manages Docker Compose services for integration tests.

    Starts Go and Baileys bridges, waits for health, provides service manager.
    Scope: session (start once, shared across all integration tests)
    """
    class DockerServicesManager:
        def __init__(self):
            self.go_url = "http://localhost:8080"
            self.baileys_url = "http://localhost:8081"

        def wait_for_service(self, service_name: str, timeout: int = 60) -> bool:
            """
            Wait for service to be healthy.

            Args:
                service_name: "go-backend" or "baileys-backend"
                timeout: Maximum time to wait in seconds

            Returns:
                True if service becomes healthy, False on timeout
            """
            url = self.go_url if service_name == "go-backend" else self.baileys_url
            health_url = f"{url}/health"

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(health_url, timeout=2)
                    if response.status_code == 200:
                        return True
                except Exception:
                    pass

                time.sleep(2)

            return False

        def get_service_port(self, service_name: str) -> int:
            """Get the port number for a service"""
            if service_name == "go-backend":
                return 8080
            elif service_name == "baileys-backend":
                return 8081
            return None

        def restart_service(self, service_name: str):
            """Restart a service (for failover testing)"""
            # Note: In actual implementation, this would use docker-compose restart
            # For now, this is a placeholder
            pass

        def stop_service(self, service_name: str):
            """Stop a service (for failover testing)"""
            # Note: In actual implementation, this would use docker-compose stop
            # For now, this is a placeholder
            pass

    manager = DockerServicesManager()

    # Wait for both services to be healthy
    # Note: This is a simplified version. In production, pytest-docker
    # would handle service startup and we'd just wait here.
    # For now, we assume services are already running or will be started manually.

    yield manager

    # Cleanup happens automatically with session scope


@pytest.fixture
def integration_database():
    """
    Provides test database for integration tests.

    Uses real database but with cleanup after each test.
    """
    import sqlite3

    # Use a test database file
    db_path = "/tmp/test_integration_messages.db"

    # Create connection
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Initialize schema
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

    yield conn

    # Cleanup: Delete all test data
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM chats")
    cursor.execute("DELETE FROM sync_checkpoints")
    conn.commit()
    conn.close()

    # Remove test database file
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def integration_test_data(integration_database) -> Dict:
    """
    Provides pre-populated test data for integration scenarios.

    Args:
        integration_database: Test database fixture

    Returns:
        Dictionary with messages, chats, contacts, communities
    """
    cursor = integration_database.cursor()

    # Insert test messages
    messages = []
    for i in range(50):
        msg = {
            "id": f"integration-msg-{i:05d}",
            "chat_jid": f"12036328{i % 5:07d}@g.us",
            "sender": f"{i}9876543210@s.whatsapp.net",
            "content": f"Integration test message {i}",
            "timestamp": 1728745200 + i * 60,
            "is_from_me": 0,
            "read_status": "unread" if i < 30 else "read",
            "message_type": "text",
            "media_path": None
        }
        messages.append(msg)

        cursor.execute("""
            INSERT INTO messages (id, chat_jid, sender, content, timestamp, is_from_me, read_status, message_type, media_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg["id"], msg["chat_jid"], msg["sender"], msg["content"],
              msg["timestamp"], msg["is_from_me"], msg["read_status"],
              msg["message_type"], msg["media_path"]))

    # Insert test chats
    chats = []
    for i in range(5):
        chat = {
            "jid": f"12036328{i:07d}@g.us",
            "name": f"Integration Test Group {i}",
            "is_group": 1,
            "unread_count": 10,
            "last_message_timestamp": 1728745200 + i * 100
        }
        chats.append(chat)

        cursor.execute("""
            INSERT INTO chats (jid, name, is_group, unread_count, last_message_timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (chat["jid"], chat["name"], chat["is_group"],
              chat["unread_count"], chat["last_message_timestamp"]))

    integration_database.commit()

    # Create test community structure
    communities = [{
        "community_jid": "120363143634035041@g.us",
        "group_jids": [f"12036328{i:07d}@g.us" for i in range(2)],
        "total_messages": 20,
        "unread_messages": 10
    }]

    return {
        "messages": messages,
        "chats": chats,
        "communities": communities,
        "contacts": [
            {"jid": f"{i}9876543210@s.whatsapp.net", "name": f"Test Contact {i}"}
            for i in range(10)
        ]
    }
