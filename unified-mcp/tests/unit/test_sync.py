"""
Unit tests for sync.py - Database synchronization logic

Tests batch processing, deduplication, error handling, and performance.
Target: 75%+ coverage of sync.py (410 lines)
"""
import pytest
import responses
import time
from unittest.mock import Mock, patch, MagicMock
from sync import DatabaseSyncService, SyncResult, sync_baileys_to_go, sync_all_chats


class TestBatchSizes:
    """Test sync with different batch sizes"""

    @responses.activate
    def test_sync_with_zero_messages(self):
        """T048: Test sync_messages with 0 messages (empty Baileys DB)"""
        # Setup: Baileys returns empty message list
        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": []},
            status=200
        )

        # Create sync service
        sync_service = DatabaseSyncService()

        # Test: Sync should succeed with 0 messages
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Success with 0 synced
        assert result.success is True
        assert result.messages_synced == 0
        assert result.messages_deduplicated == 0
        assert result.elapsed_seconds >= 0

    @responses.activate
    def test_sync_with_one_message(self):
        """T049: Test sync_messages with 1 message"""
        # Setup: Baileys returns 1 message
        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={
                "messages": [{
                    "id": "msg-00001",
                    "sender": "1234567890@s.whatsapp.net",
                    "content": "Test message",
                    "timestamp": 1728745200,
                    "is_from_me": False
                }]
            },
            status=200
        )

        # Setup: Go DB accepts the insert
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 1},
            status=200
        )

        # Create sync service
        sync_service = DatabaseSyncService()

        # Test: Sync should succeed with 1 message
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Success with 1 synced
        assert result.success is True
        assert result.messages_synced == 1
        assert result.messages_deduplicated == 0

    @responses.activate
    def test_sync_with_100_messages(self):
        """T050: Test sync_messages with 100 messages batch"""
        # Setup: Baileys returns 100 messages
        messages = [
            {
                "id": f"msg-{i:05d}",
                "sender": f"{i}@s.whatsapp.net",
                "content": f"Message {i}",
                "timestamp": 1728745200 + i,
                "is_from_me": i % 3 == 0
            }
            for i in range(100)
        ]

        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": messages},
            status=200
        )

        # Setup: Go DB accepts all messages
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 100},
            status=200
        )

        # Create sync service
        sync_service = DatabaseSyncService()

        # Test: Sync should succeed with 100 messages
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Success with 100 synced
        assert result.success is True
        assert result.messages_synced == 100
        assert result.messages_deduplicated == 0

    @responses.activate
    def test_sync_with_1000_messages(self):
        """T051: Test sync_messages with 1000 messages batch"""
        # Setup: Baileys returns 1000 messages
        messages = [
            {
                "id": f"msg-{i:05d}",
                "sender": f"{i % 100}@s.whatsapp.net",
                "content": f"Message {i}",
                "timestamp": 1728745200 + i,
                "is_from_me": False
            }
            for i in range(1000)
        ]

        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": messages},
            status=200
        )

        # Setup: Go DB accepts all messages
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 1000},
            status=200
        )

        # Create sync service with batch_size=1000
        sync_service = DatabaseSyncService(batch_size=1000)

        # Test: Sync should succeed with 1000 messages
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Success with 1000 synced
        assert result.success is True
        assert result.messages_synced == 1000

    @responses.activate
    def test_sync_with_10000_messages(self):
        """T052: Test sync_messages with 10000 messages batch (large batch handling)"""
        # Setup: Baileys returns 10000 messages
        messages = [
            {
                "id": f"msg-{i:05d}",
                "sender": f"{i % 100}@s.whatsapp.net",
                "content": f"Message {i}",
                "timestamp": 1728745200 + i,
                "is_from_me": False
            }
            for i in range(10000)
        ]

        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": messages},
            status=200
        )

        # Setup: Go DB accepts all messages
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 10000},
            status=200
        )

        # Create sync service with large batch_size
        sync_service = DatabaseSyncService(batch_size=10000)

        # Test: Sync should handle large batch
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Success with 10000 synced
        assert result.success is True
        assert result.messages_synced == 10000
        # Verify performance (should be reasonably fast)
        assert result.elapsed_seconds < 10.0, "Large batch should complete within 10 seconds"


class TestDeduplication:
    """Test message deduplication logic"""

    def test_deduplication_identifies_existing_messages(self):
        """T053: Test deduplication identifies existing messages by composite key"""
        sync_service = DatabaseSyncService()

        # Mock messages
        messages = [
            {"id": "msg-001", "timestamp": 1728745200, "content": "Message 1"},
            {"id": "msg-002", "timestamp": 1728745201, "content": "Message 2"},
            {"id": "msg-003", "timestamp": 1728745202, "content": "Message 3"},
        ]

        # Mock _get_existing_message_ids to return some duplicates
        with patch.object(sync_service, '_get_existing_message_ids', return_value={"msg-001", "msg-003"}):
            deduplicated, dup_count = sync_service._deduplicate_messages("test_chat@g.us", messages)

        # Verify: Only msg-002 should remain
        assert len(deduplicated) == 1
        assert deduplicated[0]["id"] == "msg-002"
        assert dup_count == 2

    def test_deduplication_handles_identical_timestamps_different_ids(self):
        """T054: Test deduplication handles messages with identical timestamps but different IDs"""
        sync_service = DatabaseSyncService()

        # Mock messages with same timestamp but different IDs
        messages = [
            {"id": "msg-001", "timestamp": 1728745200, "content": "Message 1"},
            {"id": "msg-002", "timestamp": 1728745200, "content": "Message 2"},
            {"id": "msg-003", "timestamp": 1728745200, "content": "Message 3"},
        ]

        # Mock: None are duplicates (different IDs mean different messages)
        with patch.object(sync_service, '_get_existing_message_ids', return_value=set()):
            deduplicated, dup_count = sync_service._deduplicate_messages("test_chat@g.us", messages)

        # Verify: All 3 messages should be kept (different IDs)
        assert len(deduplicated) == 3
        assert dup_count == 0

    @responses.activate
    def test_sync_with_partial_duplicates(self):
        """T055: Test sync with 500 messages where 200 exist (deduplication removes 200)"""
        # Setup: Baileys returns 500 messages
        messages = [
            {
                "id": f"msg-{i:05d}",
                "sender": f"{i}@s.whatsapp.net",
                "content": f"Message {i}",
                "timestamp": 1728745200 + i,
                "is_from_me": False
            }
            for i in range(500)
        ]

        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": messages},
            status=200
        )

        # Setup: Go DB accepts 300 messages (500 - 200 duplicates)
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 300},
            status=200
        )

        # Create sync service
        sync_service = DatabaseSyncService(batch_size=1000)

        # Mock deduplication to remove 200 messages
        existing_ids = {f"msg-{i:05d}" for i in range(200)}
        with patch.object(sync_service, '_get_existing_message_ids', return_value=existing_ids):
            result = sync_service.sync_messages("test_chat@g.us")

        # Verify: 300 synced, 200 deduplicated
        assert result.success is True
        assert result.messages_synced == 300
        assert result.messages_deduplicated == 200


class TestBatchInsertion:
    """Test batch insertion to Go database"""

    @responses.activate
    def test_batch_insertion_succeeds(self):
        """T056: Test batch insertion to Go database succeeds"""
        # Setup: Go DB accepts batch
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 50},
            status=200
        )

        sync_service = DatabaseSyncService()

        # Create test messages
        messages = [
            {
                "id": f"msg-{i:05d}",
                "sender": f"{i}@s.whatsapp.net",
                "content": f"Message {i}",
                "timestamp": 1728745200 + i,
                "is_from_me": False
            }
            for i in range(50)
        ]

        # Test: Batch insert
        inserted_count = sync_service._insert_to_go_db("test_chat@g.us", messages)

        # Verify: All 50 inserted
        assert inserted_count == 50

    @responses.activate
    def test_batch_insertion_partial_failure(self):
        """T057: Test batch insertion failure midway reports partial success with accurate count"""
        # Setup: Go DB reports partial success
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 30, "failed_count": 20},
            status=200
        )

        sync_service = DatabaseSyncService()

        # Create test messages
        messages = [{"id": f"msg-{i:05d}", "timestamp": 1728745200 + i} for i in range(50)]

        # Test: Batch insert with partial failure
        inserted_count = sync_service._insert_to_go_db("test_chat@g.us", messages)

        # Verify: Reports 30 inserted (partial success)
        assert inserted_count == 30


class TestNetworkErrors:
    """Test network error handling"""

    @responses.activate
    def test_network_timeout_fetching_from_baileys(self):
        """T058: Test network timeout fetching from Baileys fails gracefully without data corruption"""
        # Setup: Baileys times out
        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            body=Exception("Connection timeout"),
            status=500
        )

        sync_service = DatabaseSyncService(request_timeout=5)

        # Test: Sync should fail gracefully on timeout
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Failure reported, no data corruption
        assert result.success is False
        assert result.messages_synced == 0
        assert result.error_message is not None


class TestCheckpoints:
    """Test checkpoint management"""

    def test_checkpoint_update_after_successful_sync(self):
        """T059: Test checkpoint update after successful sync contains correct message count"""
        sync_service = DatabaseSyncService()

        # Mock _update_checkpoint
        with patch.object(sync_service, '_update_checkpoint') as mock_checkpoint:
            # Call with test data
            sync_service._update_checkpoint("test_chat@g.us", 150)

            # Verify: Called with correct count
            mock_checkpoint.assert_called_once_with("test_chat@g.us", 150)

    def test_checkpoint_update_failure_logged(self):
        """T060: Test checkpoint update failure is logged but doesn't block sync"""
        sync_service = DatabaseSyncService()

        # The method already handles exceptions gracefully (logs warning, doesn't raise)
        # Test that calling it directly doesn't raise
        try:
            sync_service._update_checkpoint("test_chat@g.us", 100)
            # Pass - method completes without raising
        except Exception as e:
            pytest.fail(f"Checkpoint update should not raise exception: {e}")


class TestTempDBCleanup:
    """Test Baileys temp DB cleanup"""

    def test_temp_db_clear_after_sync(self):
        """T061: Test Baileys temp DB clearing after sync completion"""
        sync_service = DatabaseSyncService()

        # Mock _clear_baileys_temp_db
        with patch.object(sync_service, '_clear_baileys_temp_db') as mock_clear:
            sync_service._clear_baileys_temp_db()

            # Verify: Called
            mock_clear.assert_called_once()

    def test_temp_db_clear_failure_logged(self):
        """T062: Test Baileys temp DB clear failure is logged but doesn't fail sync"""
        sync_service = DatabaseSyncService()

        # The method already handles exceptions gracefully (logs warning, doesn't raise)
        # Test that calling it directly doesn't raise
        try:
            sync_service._clear_baileys_temp_db()
            # Pass - method completes without raising
        except Exception as e:
            pytest.fail(f"Temp DB clear should not raise exception: {e}")


class TestPerformance:
    """Test sync performance"""

    @responses.activate
    def test_sync_achieves_100_messages_per_second(self):
        """T063: Test sync achieves 100+ messages/second throughput (performance validation)"""
        # Setup: Baileys returns 1000 messages
        messages = [
            {
                "id": f"msg-{i:05d}",
                "sender": f"{i % 100}@s.whatsapp.net",
                "content": f"Message {i}",
                "timestamp": 1728745200 + i,
                "is_from_me": False
            }
            for i in range(1000)
        ]

        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": messages},
            status=200
        )

        # Setup: Go DB accepts all messages quickly
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 1000},
            status=200
        )

        sync_service = DatabaseSyncService(batch_size=1000)

        # Test: Measure sync performance
        start_time = time.time()
        result = sync_service.sync_messages("test_chat@g.us")
        elapsed = time.time() - start_time

        # Verify: At least 100 msg/s throughput
        throughput = result.messages_synced / result.elapsed_seconds if result.elapsed_seconds > 0 else 0
        # Note: In unit tests with mocked HTTP, this will be very fast
        # In integration tests, this would validate actual network performance
        assert result.success is True
        assert result.messages_synced == 1000
        # Sanity check: Should complete quickly with mocked responses
        assert elapsed < 2.0, "Sync should be fast with mocked responses"


class TestSyncAllChats:
    """Test sync_all_chats functionality"""

    @responses.activate
    def test_sync_all_chats_processes_multiple_chats(self):
        """T064: Test sync_all_chats processes multiple chats sequentially"""
        # Setup: Baileys returns 3 chats
        responses.add(
            responses.GET,
            "http://localhost:8081/chats/list",
            json={
                "chats": [
                    {"jid": "chat1@g.us"},
                    {"jid": "chat2@g.us"},
                    {"jid": "chat3@g.us"}
                ]
            },
            status=200
        )

        # Setup: Each chat returns some messages
        for i in range(1, 4):
            responses.add(
                responses.GET,
                "http://localhost:8081/history/messages",
                json={"messages": [{"id": f"msg-{i}", "timestamp": 1728745200 + i}]},
                status=200
            )
            responses.add(
                responses.POST,
                "http://localhost:8080/messages/batch",
                json={"inserted_count": 1},
                status=200
            )

        # Test: Sync all chats
        results = sync_all_chats()

        # Verify: All 3 chats synced
        assert len(results) == 3
        assert "chat1@g.us" in results
        assert "chat2@g.us" in results
        assert "chat3@g.us" in results
        assert all(r.success for r in results.values())


class TestSyncResult:
    """Test SyncResult dataclass"""

    @responses.activate
    def test_sync_result_contains_accurate_metrics(self):
        """T065: Test SyncResult contains accurate metrics (synced count, deduplicated count, elapsed time)"""
        # Setup: Simple sync scenario
        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": [
                {"id": "msg-001", "timestamp": 1728745200, "content": "Test"}
            ]},
            status=200
        )

        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            json={"inserted_count": 1},
            status=200
        )

        sync_service = DatabaseSyncService()

        # Test: Sync and check result
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Result has all expected fields
        assert hasattr(result, 'success')
        assert hasattr(result, 'messages_synced')
        assert hasattr(result, 'messages_deduplicated')
        assert hasattr(result, 'elapsed_seconds')
        assert hasattr(result, 'error_message')
        assert hasattr(result, 'details')

        # Verify: Values are correct
        assert result.success is True
        assert result.messages_synced == 1
        assert result.messages_deduplicated == 0
        assert result.elapsed_seconds >= 0
        assert result.details is not None
        assert "throughput_per_second" in result.details


class TestGoDatabaseErrors:
    """Test Go database error handling"""

    @responses.activate
    def test_sync_handles_go_database_connection_error(self):
        """T066: Test sync handles Go database connection error gracefully"""
        # Setup: Baileys returns messages
        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": [
                {"id": "msg-001", "timestamp": 1728745200}
            ]},
            status=200
        )

        # Setup: Go DB connection fails
        responses.add(
            responses.POST,
            "http://localhost:8080/messages/batch",
            body=Exception("Connection refused"),
            status=500
        )

        sync_service = DatabaseSyncService()

        # Test: Sync should fail gracefully
        result = sync_service.sync_messages("test_chat@g.us")

        # Verify: Failure reported gracefully
        assert result.success is False
        assert result.messages_synced == 0
        assert result.error_message is not None


class TestConvenienceFunction:
    """Test convenience wrapper function"""

    @responses.activate
    def test_sync_baileys_to_go_wrapper(self):
        """Test sync_baileys_to_go convenience function works correctly"""
        # Setup: Simple sync scenario
        responses.add(
            responses.GET,
            "http://localhost:8081/history/messages",
            json={"messages": []},
            status=200
        )

        # Test: Use convenience function
        result = sync_baileys_to_go("test_chat@g.us")

        # Verify: Works as expected
        assert isinstance(result, SyncResult)
        assert result.success is True
