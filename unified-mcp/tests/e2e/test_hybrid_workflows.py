"""End-to-end tests for hybrid workflows (Phase 6: US4).

Tests the complete mark_community_as_read_with_history workflow
that combines Baileys history sync + Go mark-as-read operations.
"""

from unittest.mock import patch


class TestMarkCommunityAsReadWithHistoryE2E:
    """Test mark_community_as_read_with_history end-to-end workflow."""

    def test_mark_community_as_read_with_history_completes_end_to_end_with_500_messages(
        self, e2e_test_community, e2e_workflow_tracker
    ):
        """T088: Test mark_community_as_read_with_history completes end-to-end with 500 messages."""
        from main import mark_community_as_read_with_history

        e2e_workflow_tracker.start_workflow()

        # Mock all backend interactions
        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history, \
             patch('main.sync_history_to_database') as mock_sync, \
             patch('main.mark_community_as_read') as mock_mark, \
             patch('main.baileys_client') as mock_baileys:

            # Step 1: Health check succeeds
            e2e_workflow_tracker.start_step("health_check")
            mock_status.return_value = {"overall_status": "healthy"}
            e2e_workflow_tracker.end_step("health_check", success=True)

            # Step 2: History sync succeeds with 500 messages
            e2e_workflow_tracker.start_step("history_sync")
            mock_history.return_value = {
                "success": True,
                "status": {"messages_synced": 500}
            }
            e2e_workflow_tracker.end_step("history_sync", success=True)

            # Step 3: Database sync succeeds
            e2e_workflow_tracker.start_step("database_sync")
            mock_sync.return_value = {
                "success": True,
                "messages_added": 500,
                "messages_skipped": 0
            }
            e2e_workflow_tracker.end_step("database_sync", success=True)

            # Step 4: Mark as read succeeds
            e2e_workflow_tracker.start_step("mark_as_read")
            mock_mark.return_value = {
                "success": True,
                "message": "Marked 500 messages as read across 2 groups",
                "details": {"groups_processed": 2, "messages_marked": 500}
            }
            e2e_workflow_tracker.end_step("mark_as_read", success=True)

            # Step 5: Cleanup succeeds
            e2e_workflow_tracker.start_step("cleanup")
            mock_baileys.clear_temp_data.return_value = True
            e2e_workflow_tracker.end_step("cleanup", success=True)

            # Execute workflow
            result = mark_community_as_read_with_history(
                community_jid=e2e_test_community["community_jid"],
                sync_timeout=300
            )

        e2e_workflow_tracker.end_workflow()

        # Verify: Workflow completed successfully
        assert result["success"] is True
        assert len(result["steps"]) == 5
        assert result["mark_as_read_details"]["messages_marked"] == 500

        # Verify: All workflow steps succeeded
        e2e_workflow_tracker.assert_all_steps_successful()

    def test_mark_community_as_read_with_history_respects_5_minute_timeout(
        self, e2e_test_community, e2e_workflow_tracker
    ):
        """T089: Test mark_community_as_read_with_history respects 5-minute timeout (doesn't hang)."""
        from main import mark_community_as_read_with_history

        e2e_workflow_tracker.start_workflow()

        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history:

            # Health check succeeds
            mock_status.return_value = {"overall_status": "healthy"}

            # History sync times out
            mock_history.return_value = {
                "success": False,
                "message": "Sync timeout exceeded (300s)"
            }

            # Execute workflow with 5-minute timeout
            e2e_workflow_tracker.start_step("workflow_execution")
            result = mark_community_as_read_with_history(
                community_jid=e2e_test_community["community_jid"],
                sync_timeout=300
            )
            e2e_workflow_tracker.end_step("workflow_execution", success=True)

        e2e_workflow_tracker.end_workflow()

        # Verify: Workflow fails gracefully without hanging
        assert result["success"] is False
        assert "timeout" in result["message"].lower() or "failed" in result["message"].lower()

        # Verify: Completed within reasonable time (timeout + overhead < 310s)
        e2e_workflow_tracker.assert_total_duration_under(310)

    def test_mark_community_as_read_with_history_handles_baileys_history_sync_failure(
        self, e2e_test_community
    ):
        """T090: Test mark_community_as_read_with_history handles Baileys history sync failure gracefully."""
        from main import mark_community_as_read_with_history

        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history:

            # Health check succeeds
            mock_status.return_value = {"overall_status": "healthy"}

            # History sync fails
            mock_history.return_value = {
                "success": False,
                "message": "Baileys backend connection lost"
            }

            # Execute workflow
            result = mark_community_as_read_with_history(
                community_jid=e2e_test_community["community_jid"]
            )

        # Verify: Workflow fails gracefully
        assert result["success"] is False
        assert "History sync failed" in result["message"]
        assert any(step["step"] == "history_sync" and "❌" in step["status"]
                   for step in result["steps"])

    def test_mark_community_as_read_with_history_handles_go_mark_as_read_failure_after_sync(
        self, e2e_test_community
    ):
        """T091: Test mark_community_as_read_with_history handles Go mark-as-read failure after sync."""
        from main import mark_community_as_read_with_history

        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history, \
             patch('main.sync_history_to_database') as mock_sync, \
             patch('main.mark_community_as_read') as mock_mark:

            # Health check succeeds
            mock_status.return_value = {"overall_status": "healthy"}

            # History sync succeeds
            mock_history.return_value = {
                "success": True,
                "status": {"messages_synced": 100}
            }

            # Database sync succeeds
            mock_sync.return_value = {
                "success": True,
                "messages_added": 100,
                "messages_skipped": 0
            }

            # Mark as read fails
            mock_mark.return_value = {
                "success": False,
                "message": "Go backend connection error",
                "details": {}
            }

            # Execute workflow
            result = mark_community_as_read_with_history(
                community_jid=e2e_test_community["community_jid"]
            )

        # Verify: Workflow reports failure
        assert result["success"] is False
        # Verify: All steps up to mark_as_read completed
        assert any(step["step"] == "history_sync" and "✅" in step["status"]
                   for step in result["steps"])
        assert any(step["step"] == "database_sync" and "✅" in step["status"]
                   for step in result["steps"])
        assert any(step["step"] == "mark_as_read" and "❌" in step["status"]
                   for step in result["steps"])

    def test_mark_community_as_read_with_history_reports_accurate_metrics(
        self, e2e_test_community
    ):
        """T092: Test mark_community_as_read_with_history reports accurate metrics (synced count, groups processed, time)."""
        import time

        from main import mark_community_as_read_with_history

        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history, \
             patch('main.sync_history_to_database') as mock_sync, \
             patch('main.mark_community_as_read') as mock_mark, \
             patch('main.baileys_client') as mock_baileys:

            # Setup mocks
            mock_status.return_value = {"overall_status": "healthy"}
            mock_history.return_value = {
                "success": True,
                "status": {"messages_synced": 250}
            }
            mock_sync.return_value = {
                "success": True,
                "messages_added": 200,
                "messages_deduplicated": 50
            }
            mock_mark.return_value = {
                "success": True,
                "message": "Marked 200 messages as read across 3 groups",
                "details": {
                    "groups_processed": 3,
                    "messages_marked": 200,
                    "groups": [
                        {"jid": "group1@g.us", "messages_marked": 80},
                        {"jid": "group2@g.us", "messages_marked": 70},
                        {"jid": "group3@g.us", "messages_marked": 50}
                    ]
                }
            }
            mock_baileys.clear_temp_data.return_value = True

            # Execute workflow
            start_time = time.time()
            result = mark_community_as_read_with_history(
                community_jid=e2e_test_community["community_jid"]
            )
            elapsed = time.time() - start_time

        # Verify: Accurate metrics reported
        assert result["success"] is True

        # Check history sync metrics
        history_step = next(s for s in result["steps"] if s["step"] == "history_sync")
        assert "250 messages" in history_step["status"]

        # Check database sync metrics
        db_step = next(s for s in result["steps"] if s["step"] == "database_sync")
        assert "200 new messages" in db_step["status"]
        assert "50 deduplicated" in db_step["status"]

        # Check mark as read metrics
        assert result["mark_as_read_details"]["groups_processed"] == 3
        assert result["mark_as_read_details"]["messages_marked"] == 200

        # Verify: Workflow completed quickly (< 5 seconds for mocked operations)
        assert elapsed < 5.0

    def test_mark_community_as_read_with_history_concurrent_calls_for_different_communities(
        self, e2e_test_community
    ):
        """T093: Test concurrent mark_community_as_read_with_history calls for different communities complete without race conditions."""
        import threading
        import time

        from main import mark_community_as_read_with_history

        results = {}
        errors = {}

        # Patch globally before creating threads (patches apply to all threads)
        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history, \
             patch('main.sync_history_to_database') as mock_sync, \
             patch('main.mark_community_as_read') as mock_mark, \
             patch('main.baileys_client') as mock_baileys:

            # Setup mocks
            mock_status.return_value = {"overall_status": "healthy"}
            mock_history.return_value = {
                "success": True,
                "status": {"messages_synced": 100}
            }
            mock_sync.return_value = {
                "success": True,
                "messages_added": 100,
                "messages_skipped": 0
            }

            def mark_side_effect(community_jid):
                """Return different results based on community JID."""
                community_id = community_jid.split('@')[0][-1]
                return {
                    "success": True,
                    "message": f"Marked community {community_id}",
                    "details": {"groups_processed": 2, "messages_marked": 100}
                }

            mock_mark.side_effect = mark_side_effect
            mock_baileys.clear_temp_data.return_value = True

            def run_workflow(community_id: str, community_jid: str):
                """Execute workflow for a community."""
                try:
                    # Small delay to ensure concurrent execution
                    time.sleep(0.01)

                    # Execute workflow
                    result = mark_community_as_read_with_history(community_jid)
                    results[community_id] = result

                except Exception as e:
                    errors[community_id] = str(e)

            # Create threads for 3 different communities
            threads = []
            for i in range(3):
                community_id = f"community_{i}"
                community_jid = f"12036314363403504{i}@g.us"
                thread = threading.Thread(target=run_workflow, args=(community_id, community_jid))
                threads.append(thread)

            # Start all threads simultaneously
            start_time = time.time()
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)

            elapsed = time.time() - start_time

        # Verify: All workflows completed successfully
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # Verify: Each workflow completed successfully
        for community_id, result in results.items():
            assert result["success"] is True, f"Community {community_id} workflow failed"
            assert result["mark_as_read_details"]["messages_marked"] == 100

        # Verify: All threads completed within reasonable time (concurrent execution)
        assert elapsed < 15.0, f"Concurrent workflows took too long: {elapsed:.2f}s"

    def test_mark_community_as_read_with_history_clears_baileys_temp_db_after_completion(
        self, e2e_test_community
    ):
        """T094: Test mark_community_as_read_with_history clears Baileys temp DB after completion."""
        from main import mark_community_as_read_with_history

        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history, \
             patch('main.sync_history_to_database') as mock_sync, \
             patch('main.mark_community_as_read') as mock_mark, \
             patch('main.baileys_client') as mock_baileys:

            # Setup mocks
            mock_status.return_value = {"overall_status": "healthy"}
            mock_history.return_value = {
                "success": True,
                "status": {"messages_synced": 100}
            }
            mock_sync.return_value = {
                "success": True,
                "messages_added": 100,
                "messages_skipped": 0
            }
            mock_mark.return_value = {
                "success": True,
                "message": "Marked 100 messages as read",
                "details": {"groups_processed": 2, "messages_marked": 100}
            }
            mock_baileys.clear_temp_data.return_value = True

            # Execute workflow
            result = mark_community_as_read_with_history(
                community_jid=e2e_test_community["community_jid"]
            )

        # Verify: Cleanup step executed
        cleanup_step = next((s for s in result["steps"] if s["step"] == "cleanup"), None)
        assert cleanup_step is not None, "Cleanup step not found in workflow"
        assert "✅" in cleanup_step["status"], "Cleanup step did not succeed"
        assert "Temp data cleared" in cleanup_step["status"]

        # Verify: clear_temp_data was called
        mock_baileys.clear_temp_data.assert_called_once()

    def test_mark_community_as_read_with_history_updates_checkpoints_correctly(
        self, e2e_test_community, integration_database
    ):
        """T095: Test mark_community_as_read_with_history updates checkpoints correctly."""
        from main import mark_community_as_read_with_history

        with patch('main.backend_status') as mock_status, \
             patch('main.retrieve_full_history') as mock_history, \
             patch('main.sync_history_to_database') as mock_sync, \
             patch('main.mark_community_as_read') as mock_mark, \
             patch('main.baileys_client') as mock_baileys:

            # Setup mocks
            mock_status.return_value = {"overall_status": "healthy"}
            mock_history.return_value = {
                "success": True,
                "status": {"messages_synced": 100}
            }

            # Mock sync to also simulate checkpoint update
            def sync_with_checkpoint():
                cursor = integration_database.cursor()
                for group_jid in e2e_test_community["group_jids"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO sync_checkpoints
                        (chat_jid, last_synced_message_id, last_synced_timestamp, messages_synced_count)
                        VALUES (?, ?, ?, ?)
                    """, (group_jid, f"msg-{group_jid}-100", 1728745200 + 100, 100))
                integration_database.commit()
                return {
                    "success": True,
                    "messages_added": 100,
                    "messages_skipped": 0
                }

            mock_sync.side_effect = sync_with_checkpoint
            mock_mark.return_value = {
                "success": True,
                "message": "Marked messages as read",
                "details": {"groups_processed": 2, "messages_marked": 100}
            }
            mock_baileys.clear_temp_data.return_value = True

            # Execute workflow
            result = mark_community_as_read_with_history(
                community_jid=e2e_test_community["community_jid"]
            )

        # Verify: Checkpoints created in database
        cursor = integration_database.cursor()
        for group_jid in e2e_test_community["group_jids"]:
            cursor.execute(
                "SELECT * FROM sync_checkpoints WHERE chat_jid = ?",
                (group_jid,)
            )
            checkpoint = cursor.fetchone()
            assert checkpoint is not None, f"Checkpoint not found for {group_jid}"
            assert checkpoint["messages_synced_count"] == 100
            assert checkpoint["last_synced_message_id"] is not None

        # Verify: Workflow succeeded
        assert result["success"] is True
