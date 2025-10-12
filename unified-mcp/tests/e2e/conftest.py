"""
End-to-end test fixtures for complete workflow testing.

These fixtures provide test communities and workflow tracking
for validating complete hybrid workflows.
"""

import pytest
import time
import os
import sqlite3
from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class WorkflowStep:
    """Represents a single step in an e2e workflow"""
    name: str
    start_time: float = None
    end_time: float = None
    duration: float = None
    error: str = None
    success: bool = None


@pytest.fixture
def e2e_test_community():
    """
    Provides complete test community for e2e hybrid workflow tests.

    Returns:
        Dictionary with community structure and test data
    """
    # Return test community structure (no database required for mocked e2e tests)
    community_jid = "120363143634035041@g.us"
    group_jids = [
        "120363281234567890@g.us",
        "120363289876543210@g.us"
    ]

    yield {
        "community_jid": community_jid,
        "group_jids": group_jids,
        "total_messages": 100,
        "unread_messages": 100
    }


@pytest.fixture
def e2e_workflow_tracker():
    """
    Tracks execution steps and timing for e2e workflow tests.

    Returns:
        Tracker object for recording workflow steps and generating reports
    """
    class WorkflowTracker:
        def __init__(self):
            self.steps: List[WorkflowStep] = []
            self.workflow_start: float = None
            self.workflow_end: float = None

        def start_workflow(self):
            """Start tracking the overall workflow"""
            self.workflow_start = time.time()

        def end_workflow(self):
            """End tracking the overall workflow"""
            self.workflow_end = time.time()

        def start_step(self, step_name: str):
            """Start a workflow step"""
            step = WorkflowStep(name=step_name, start_time=time.time())
            self.steps.append(step)

        def end_step(self, step_name: str, success: bool = True):
            """End a workflow step"""
            for step in reversed(self.steps):
                if step.name == step_name and step.end_time is None:
                    step.end_time = time.time()
                    step.duration = step.end_time - step.start_time
                    step.success = success
                    break

        def record_error(self, step_name: str, error: str):
            """Record an error for a step"""
            for step in reversed(self.steps):
                if step.name == step_name:
                    step.error = error
                    step.success = False
                    if step.end_time is None:
                        step.end_time = time.time()
                        step.duration = step.end_time - step.start_time
                    break

        def get_report(self) -> Dict:
            """
            Generate workflow execution report.

            Returns:
                Dictionary with step-by-step execution details
            """
            total_duration = None
            if self.workflow_start and self.workflow_end:
                total_duration = self.workflow_end - self.workflow_start

            steps_report = {}
            for step in self.steps:
                steps_report[step.name] = {
                    "duration": step.duration,
                    "success": step.success,
                    "error": step.error
                }

            return {
                "total_duration": total_duration,
                "steps": steps_report,
                "total_steps": len(self.steps),
                "successful_steps": sum(1 for s in self.steps if s.success),
                "failed_steps": sum(1 for s in self.steps if s.success is False),
                "overall_success": all(s.success for s in self.steps if s.success is not None)
            }

        def assert_all_steps_successful(self):
            """Assert that all workflow steps completed successfully"""
            report = self.get_report()
            assert report["overall_success"], (
                f"Workflow had {report['failed_steps']} failed steps: "
                f"{[name for name, details in report['steps'].items() if not details['success']]}"
            )

        def assert_total_duration_under(self, max_seconds: float):
            """Assert that total workflow completed within time limit"""
            report = self.get_report()
            assert report["total_duration"] is not None, "Workflow not completed"
            assert report["total_duration"] < max_seconds, (
                f"Workflow took {report['total_duration']:.2f}s, "
                f"exceeding {max_seconds}s limit"
            )

    return WorkflowTracker()


@pytest.fixture
def integration_database():
    """
    Provides test database for e2e tests that need database verification.

    Uses real database but with cleanup after each test.
    """
    # Use a test database file
    db_path = "/tmp/test_e2e_messages.db"

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
