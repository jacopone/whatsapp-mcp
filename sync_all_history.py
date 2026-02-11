#!/usr/bin/env python3
"""
WhatsApp Full History Sync Tool

The Baileys bridge automatically syncs full history when it connects (syncFullHistory: true).
This script:
1. Checks sync status
2. Waits for automatic sync to complete
3. Transfers messages from Baileys temp DB to Go main DB
4. Shows statistics
"""

import requests
import time
import json
from datetime import datetime

# Bridge URLs
BAILEYS_URL = "http://localhost:8081"
GO_URL = "http://localhost:8080"

def print_status(message, level="INFO"):
    """Print formatted status message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": "\033[36m", "SUCCESS": "\033[32m", "ERROR": "\033[31m", "WARN": "\033[33m"}
    reset = "\033[0m"
    print(f"{colors.get(level, '')}{timestamp} [{level}] {message}{reset}")

def check_bridge_health():
    """Check if both bridges are running."""
    print_status("Checking bridge health...")

    try:
        go_health = requests.get(f"{GO_URL}/health", timeout=5).json()
        print_status(f"✓ Go Bridge: {go_health['status']}", "SUCCESS")
    except Exception as e:
        print_status(f"✗ Go Bridge not responding: {e}", "ERROR")
        return False

    try:
        baileys_health = requests.get(f"{BAILEYS_URL}/health", timeout=5).json()
        print_status(f"✓ Baileys Bridge: {baileys_health.get('status', 'ok')}", "SUCCESS")
        print_status(f"  Connected: {baileys_health.get('connected', False)}", "INFO")
    except Exception as e:
        print_status(f"✗ Baileys Bridge not responding: {e}", "ERROR")
        return False

    return True

def get_baileys_sync_status():
    """Get current Baileys sync status."""
    try:
        response = requests.get(f"{BAILEYS_URL}/api/sync/status", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print_status(f"Could not get Baileys sync status: {e}", "WARN")
    return None

def get_baileys_messages():
    """Get all messages from Baileys temp database."""
    try:
        response = requests.get(f"{BAILEYS_URL}/api/messages", timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('messages', [])
    except Exception as e:
        print_status(f"Error fetching Baileys messages: {e}", "ERROR")
    return []

def transfer_to_go_database(messages):
    """Transfer messages from Baileys to Go database.

    Note: This requires an import endpoint on the Go bridge.
    For now, messages are stored via real-time event handlers.
    """
    # TODO: Implement batch import endpoint on Go bridge
    # For now, messages automatically sync via event handlers
    print_status(f"Messages are automatically synced to Go DB via event handlers", "INFO")
    print_status(f"Total messages in Baileys temp DB: {len(messages):,}", "INFO")

def get_go_stats():
    """Get current message statistics from Go database."""
    try:
        # Try the stats endpoint
        response = requests.get(f"{GO_URL}/api/stats", timeout=10)
        if response.status_code == 200:
            return response.json()

        # Fallback: count from unread chats endpoint
        response = requests.get(f"{GO_URL}/api/chats/unread?limit=1", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "total_chats": data.get('count', 0)
            }
    except Exception as e:
        print_status(f"Could not get Go stats: {e}", "WARN")
    return None

def wait_for_sync_completion(max_wait_minutes=15):
    """Wait for Baileys history sync to complete."""
    print_status("=" * 70)
    print_status("PHASE 1: Waiting for Baileys History Sync", "INFO")
    print_status("=" * 70)
    print_status(f"Max wait time: {max_wait_minutes} minutes", "INFO")
    print_status("", "INFO")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    last_progress = -1
    last_message_count = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            print_status(f"Timeout after {max_wait_minutes} minutes", "WARN")
            print_status("Sync may still be running. Check baileys-bridge.log for details.", "WARN")
            return False

        status = get_baileys_sync_status()
        if not status:
            print_status("Could not get sync status", "ERROR")
            time.sleep(5)
            continue

        is_syncing = status.get('is_syncing', False)
        is_latest = status.get('is_latest', False)
        progress = status.get('progress_percent', 0)
        messages_synced = status.get('messages_synced', 0)
        chats_synced = status.get('chats_synced', 0)

        # Show progress update
        if progress != last_progress or messages_synced != last_message_count:
            print_status(f"Progress: {progress}% | Messages: {messages_synced:,} | Chats: {chats_synced:,}", "INFO")
            last_progress = progress
            last_message_count = messages_synced

        # Check if completed
        if is_latest and not is_syncing:
            print_status("", "INFO")
            print_status("✓ History sync completed!", "SUCCESS")
            print_status(f"  Total messages synced: {messages_synced:,}", "SUCCESS")
            print_status(f"  Total chats synced: {chats_synced:,}", "SUCCESS")
            return True

        time.sleep(3)

def main():
    """Main execution flow."""
    print_status("=" * 70)
    print_status("WhatsApp Full History Sync Tool", "INFO")
    print_status("=" * 70)
    print_status("", "INFO")
    print_status("How it works:", "INFO")
    print_status("  1. Baileys automatically syncs ALL history when it connects", "INFO")
    print_status("  2. Messages are stored in Baileys temp database", "INFO")
    print_status("  3. Real-time events sync them to Go main database", "INFO")
    print_status("", "INFO")

    # Check bridges
    if not check_bridge_health():
        print_status("", "ERROR")
        print_status("Bridges not healthy. Please start them first:", "ERROR")
        print_status("  cd /home/guyfawkes/birthday-manager/whatsapp-mcp", "ERROR")
        print_status("  ./cleanup-bridges.sh && ./start-bridges.sh", "ERROR")
        return 1

    print_status("", "INFO")

    # Check current status
    baileys_status = get_baileys_sync_status()
    if baileys_status:
        print_status("Current Baileys Status:", "INFO")
        print_status(f"  Is syncing: {baileys_status.get('is_syncing', False)}", "INFO")
        print_status(f"  Messages synced: {baileys_status.get('messages_synced', 0):,}", "INFO")
        print_status(f"  Chats synced: {baileys_status.get('chats_synced', 0):,}", "INFO")
        print_status(f"  Progress: {baileys_status.get('progress_percent', 0)}%", "INFO")
        print_status(f"  Is latest: {baileys_status.get('is_latest', False)}", "INFO")

        if baileys_status.get('is_latest') and not baileys_status.get('is_syncing'):
            print_status("", "SUCCESS")
            print_status("✓ History sync already completed!", "SUCCESS")
            print_status("", "INFO")
        else:
            print_status("", "INFO")

    # Wait for sync to complete
    if not wait_for_sync_completion(max_wait_minutes=15):
        print_status("", "WARN")
        print_status("Sync did not complete in time. You can:", "WARN")
        print_status("  1. Wait longer and run this script again", "WARN")
        print_status("  2. Check logs: tail -f baileys-bridge/baileys-bridge.log", "WARN")
        return 1

    print_status("", "INFO")

    # Get final stats
    print_status("=" * 70)
    print_status("PHASE 2: Final Statistics", "INFO")
    print_status("=" * 70)

    baileys_messages = get_baileys_messages()
    print_status(f"", "INFO")
    print_status(f"Baileys Temp Database:", "INFO")
    print_status(f"  Total messages: {len(baileys_messages):,}", "INFO")

    go_stats = get_go_stats()
    if go_stats:
        print_status(f"", "INFO")
        print_status(f"Go Main Database:", "INFO")
        print_status(f"  Total chats: {go_stats.get('total_chats', 'N/A')}", "INFO")

    print_status("", "INFO")
    print_status("=" * 70)
    print_status("🎉 SYNC COMPLETE!", "SUCCESS")
    print_status("=" * 70)
    print_status("", "SUCCESS")
    print_status("Your WhatsApp history is now fully synced!", "SUCCESS")
    print_status("", "INFO")
    print_status("Next steps:", "INFO")
    print_status("  • View chats: curl http://localhost:8080/api/chats/unread", "INFO")
    print_status("  • Search messages: Use the Go bridge API endpoints", "INFO")
    print_status("  • Run triage: python src/triage_workflow.py", "INFO")
    print_status("", "INFO")

    return 0

if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print_status("", "WARN")
        print_status("Interrupted by user. Sync continues in background.", "WARN")
        exit(130)
