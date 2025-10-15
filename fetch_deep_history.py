#!/usr/bin/env python3
"""
WhatsApp Deep History Fetcher

Fetches older messages (2010-2015 era) using Baileys' on-demand history sync.
This script:
1. Finds the oldest message for each chat in your database
2. Requests older messages from WhatsApp using fetchMessageHistory
3. Repeats until reaching target year or WhatsApp's limit

NOTE: WhatsApp's servers may not have all history. Messages older than
      1-2 years are often unavailable unless backed up to Google Drive.
"""

import requests
import sqlite3
import time
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Configuration
BAILEYS_URL = "http://localhost:8081"
GO_URL = "http://localhost:8080"
GO_DB_PATH = "whatsapp-mcp/whatsapp-bridge/store/messages.db"

# Fetch parameters
MESSAGES_PER_REQUEST = 100  # How many messages to request at once
MAX_ITERATIONS = 10         # Max iterations per chat (prevent infinite loops)
TARGET_YEAR = 2015          # Try to fetch back to this year
DELAY_BETWEEN_REQUESTS = 2  # Seconds to wait between requests

def print_status(message: str, level: str = "INFO"):
    """Print formatted status message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": "\033[36m",
        "SUCCESS": "\033[32m",
        "ERROR": "\033[31m",
        "WARN": "\033[33m",
        "PROGRESS": "\033[35m"
    }
    reset = "\033[0m"
    print(f"{colors.get(level, '')}{timestamp} [{level}] {message}{reset}")


def get_oldest_messages_per_chat() -> List[Dict]:
    """Query Go database for oldest message in each chat."""
    print_status("Querying database for oldest messages per chat...")

    conn = sqlite3.connect(GO_DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT
            chat_jid,
            id as message_id,
            timestamp,
            is_from_me,
            COUNT(*) as total_messages_in_chat
        FROM messages
        WHERE timestamp IS NOT NULL
        GROUP BY chat_jid
        HAVING MIN(timestamp) = timestamp
        ORDER BY timestamp ASC
        LIMIT 50
    """

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    chats = []
    for row in results:
        chat_jid, message_id, timestamp_str, is_from_me, total_messages = row

        # Parse timestamp
        try:
            ts = datetime.fromisoformat(timestamp_str.replace('+00:00', ''))
            ts_ms = int(ts.timestamp() * 1000)
        except:
            print_status(f"⚠️  Could not parse timestamp for {chat_jid}: {timestamp_str}", "WARN")
            continue

        chats.append({
            'chat_jid': chat_jid,
            'oldest_message_id': message_id,
            'oldest_timestamp': timestamp_str,
            'oldest_timestamp_ms': ts_ms,
            'oldest_year': ts.year,
            'is_from_me': bool(is_from_me),
            'total_messages': total_messages
        })

    return chats


def request_older_messages(chat_jid: str, oldest_msg_id: str, oldest_ts_ms: int, from_me: bool, count: int = 100) -> bool:
    """
    Request older messages from Baileys using fetchMessageHistory.

    Returns True if request was successful, False otherwise.
    """
    try:
        # Call Baileys bridge to trigger fetchMessageHistory
        # NOTE: This requires implementing the endpoint in Baileys bridge
        response = requests.post(
            f"{BAILEYS_URL}/api/history/fetch-older",
            json={
                "chat_jid": chat_jid,
                "oldest_message_id": oldest_msg_id,
                "oldest_timestamp_ms": oldest_ts_ms,
                "from_me": from_me,
                "count": count
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_status(f"✓ Requested {count} older messages for {chat_jid}", "SUCCESS")
            return True
        else:
            print_status(f"✗ Failed to request history for {chat_jid}: HTTP {response.status_code}", "ERROR")
            return False

    except requests.exceptions.ConnectionError:
        print_status(f"✗ Baileys bridge not responding. Endpoint may not be implemented yet.", "ERROR")
        return False
    except Exception as e:
        print_status(f"✗ Error requesting history for {chat_jid}: {e}", "ERROR")
        return False


def check_if_endpoint_exists() -> bool:
    """Check if the deep history endpoint is implemented."""
    try:
        response = requests.get(f"{BAILEYS_URL}/health", timeout=5)
        if response.status_code == 200:
            # Try the endpoint
            test_response = requests.post(
                f"{BAILEYS_URL}/api/history/fetch-older",
                json={"chat_jid": "test"},
                timeout=5
            )
            # Even a 400/404 means the server is there
            return test_response.status_code != 404
    except:
        pass
    return False


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description="Fetch deep WhatsApp message history")
    parser.add_argument('--yes', '-y', action='store_true', help="Skip confirmation prompt")
    parser.add_argument('--limit', type=int, default=50, help="Limit number of chats to process (default: 50)")
    args = parser.parse_args()

    print_status("=" * 70)
    print_status("WhatsApp Deep History Fetcher", "INFO")
    print_status("=" * 70)
    print_status("", "INFO")
    print_status(f"Target: Fetch messages back to year {TARGET_YEAR}", "INFO")
    print_status(f"Batch size: {MESSAGES_PER_REQUEST} messages per request", "INFO")
    print_status(f"Max iterations per chat: {MAX_ITERATIONS}", "INFO")
    print_status("", "INFO")

    # Check if endpoint exists
    if not check_if_endpoint_exists():
        print_status("", "ERROR")
        print_status("⚠️  ENDPOINT NOT IMPLEMENTED YET", "ERROR")
        print_status("", "ERROR")
        print_status("The /api/history/fetch-older endpoint needs to be added to Baileys bridge.", "INFO")
        print_status("", "INFO")
        print_status("WHAT'S NEEDED:", "INFO")
        print_status("1. Add endpoint to baileys-bridge/src/main.ts", "INFO")
        print_status("2. Implement sock.fetchMessageHistory() call", "INFO")
        print_status("3. Handle messaging-history.set event with syncType=ON_DEMAND", "INFO")
        print_status("", "INFO")
        print_status("See DEEP_HISTORY_IMPLEMENTATION.md for full instructions", "INFO")
        return 1

    # Get oldest messages
    chats = get_oldest_messages_per_chat()
    print_status(f"Found {len(chats)} chats with messages", "SUCCESS")
    print_status("", "INFO")

    # Show chats sorted by oldest message
    print_status("Chats with oldest messages:", "INFO")
    for i, chat in enumerate(chats[:10], 1):
        year = chat['oldest_year']
        total = chat['total_messages']
        jid = chat['chat_jid']
        print_status(f"  {i}. {jid[:30]:30} | Oldest: {year} | Total: {total:,} messages", "INFO")

    if len(chats) > 10:
        print_status(f"  ... and {len(chats) - 10} more chats", "INFO")

    print_status("", "INFO")

    # Ask user to proceed
    if not args.yes:
        response = input("Fetch deep history for all chats? (y/N): ")
        if response.lower() != 'y':
            print_status("Cancelled by user", "WARN")
            return 0
    else:
        print_status("Auto-confirmed with --yes flag", "INFO")

    print_status("", "INFO")
    print_status("=" * 70, "PROGRESS")
    print_status("Starting Deep History Fetch", "PROGRESS")
    print_status("=" * 70, "PROGRESS")
    print_status("", "INFO")

    # Process each chat
    total_requests = 0
    successful_requests = 0

    for i, chat in enumerate(chats, 1):
        chat_jid = chat['chat_jid']
        oldest_year = chat['oldest_year']

        print_status(f"[{i}/{len(chats)}] Processing {chat_jid}", "PROGRESS")
        print_status(f"  Current oldest message: {chat['oldest_timestamp']} ({oldest_year})", "INFO")

        if oldest_year <= TARGET_YEAR:
            print_status(f"  ✓ Already has messages from {oldest_year} <= {TARGET_YEAR}, skipping", "SUCCESS")
            continue

        # Fetch older messages in iterations
        for iteration in range(MAX_ITERATIONS):
            print_status(f"  Iteration {iteration + 1}/{MAX_ITERATIONS}: Requesting {MESSAGES_PER_REQUEST} older messages...", "INFO")

            success = request_older_messages(
                chat_jid,
                chat['oldest_message_id'],
                chat['oldest_timestamp_ms'],
                chat['is_from_me'],
                MESSAGES_PER_REQUEST
            )

            total_requests += 1
            if success:
                successful_requests += 1

            # Wait for messages to arrive
            print_status(f"  Waiting {DELAY_BETWEEN_REQUESTS}s for messages to sync...", "INFO")
            time.sleep(DELAY_BETWEEN_REQUESTS)

            # Check if we got new messages (would need to query DB again)
            # For now, just continue iterations
            # TODO: Check if new older messages arrived

        print_status("", "INFO")

    print_status("=" * 70, "SUCCESS")
    print_status("Deep History Fetch Complete!", "SUCCESS")
    print_status("=" * 70, "SUCCESS")
    print_status("", "INFO")
    print_status(f"Total requests made: {total_requests}", "INFO")
    print_status(f"Successful requests: {successful_requests}", "INFO")
    print_status("", "INFO")
    print_status("Next steps:", "INFO")
    print_status("1. Wait 5-10 minutes for messages to sync", "INFO")
    print_status("2. Run this script again to check progress", "INFO")
    print_status("3. Repeat until messages reach your target year", "INFO")
    print_status("", "INFO")

    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print_status("", "WARN")
        print_status("Interrupted by user", "WARN")
        exit(130)
