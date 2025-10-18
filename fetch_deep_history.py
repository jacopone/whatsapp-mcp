#!/usr/bin/env python3
"""
WhatsApp Deep History Fetcher - Bulk Sync Edition

Fetches older messages using Baileys' on-demand history sync with bulk API.
This script:
1. Finds chats with oldest messages in your database
2. Submits bulk sync requests to Baileys bridge (up to 50 chats at a time)
3. Monitors progress with rich progress bars
4. Retries failed syncs individually

Updated for Phase 4: Uses /history/sync/bulk endpoint with progress monitoring
"""

import requests
import sqlite3
import time
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel

# Configuration
BAILEYS_URL = "http://localhost:8081"
GO_DB_PATH = "whatsapp-bridge/store/messages.db"

# Fetch parameters
MAX_MESSAGES_PER_CHAT = 5000    # Maximum messages to fetch per conversation
BATCH_SIZE = 50                  # Number of chats to sync in parallel (bulk API limit)
POLL_INTERVAL = 5                # Seconds between status checks
MAX_RETRIES = 3                  # Retry failed syncs this many times

console = Console()


def print_header():
    """Print formatted header."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]WhatsApp Deep History Fetcher[/bold cyan]\n"
        "[dim]Bulk Sync Edition - Phase 4[/dim]",
        border_style="cyan"
    ))
    console.print()


def get_chats_to_sync(limit: int = None) -> List[Dict]:
    """Query Go database for chats with messages to sync."""
    console.print(f"[cyan]📊 Querying database for chats...[/cyan]")

    conn = sqlite3.connect(GO_DB_PATH)
    cursor = conn.cursor()

    # Get all distinct chat_jids with their oldest message timestamp
    query = """
        SELECT
            chat_jid,
            COUNT(*) as message_count,
            MIN(timestamp) as oldest_timestamp,
            MAX(timestamp) as newest_timestamp
        FROM messages
        WHERE timestamp IS NOT NULL
        GROUP BY chat_jid
        ORDER BY oldest_timestamp ASC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    chats = []
    for row in results:
        chat_jid, message_count, oldest_ts, newest_ts = row

        # Parse timestamp
        try:
            oldest_dt = datetime.fromisoformat(oldest_ts.replace('+00:00', '').replace('+01:00', '').replace('+02:00', ''))
            newest_dt = datetime.fromisoformat(newest_ts.replace('+00:00', '').replace('+01:00', '').replace('+02:00', ''))
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not parse timestamp for {chat_jid}: {e}[/yellow]")
            continue

        chats.append({
            'chat_jid': chat_jid,
            'message_count': message_count,
            'oldest_timestamp': oldest_ts,
            'newest_timestamp': newest_ts,
            'oldest_year': oldest_dt.year,
            'newest_year': newest_dt.year,
            'is_group': '@g.us' in chat_jid
        })

    return chats


def check_baileys_health() -> bool:
    """Check if Baileys bridge is running and connected."""
    try:
        response = requests.get(f"{BAILEYS_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('connected', False)
        return False
    except:
        return False


def start_bulk_sync(chat_jids: List[str], max_messages: int = 5000) -> Dict:
    """Start bulk sync for multiple chats."""
    try:
        response = requests.post(
            f"{BAILEYS_URL}/history/sync/bulk",
            json={
                "chat_jids": chat_jids,
                "max_messages": max_messages
            },
            timeout=30
        )

        if response.status_code == 202:
            return response.json()
        else:
            console.print(f"[red]✗ Bulk sync failed: HTTP {response.status_code}[/red]")
            console.print(f"[dim]{response.text}[/dim]")
            return None

    except Exception as e:
        console.print(f"[red]✗ Error starting bulk sync: {e}[/red]")
        return None


def get_bulk_sync_status(sync_ids: List[str]) -> Dict:
    """Get status for multiple sync operations."""
    try:
        response = requests.get(
            f"{BAILEYS_URL}/history/sync/bulk/status",
            params={"sync_ids": ",".join(sync_ids)},
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return None

    except Exception as e:
        console.print(f"[red]✗ Error getting sync status: {e}[/red]")
        return None


def monitor_bulk_sync(sync_ids: List[str], total_chats: int):
    """Monitor bulk sync progress with rich progress bar."""

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:

        task = progress.add_task(
            "[cyan]Syncing conversations...",
            total=total_chats
        )

        completed_previous = 0

        while not progress.finished:
            status = get_bulk_sync_status(sync_ids)

            if not status:
                console.print("[yellow]⚠️  Could not get sync status, retrying...[/yellow]")
                time.sleep(POLL_INTERVAL)
                continue

            completed = status.get('completed', 0)
            in_progress = status.get('in_progress', 0)
            failed = status.get('failed', 0)
            total_messages = status.get('total_messages_synced', 0)

            # Update progress
            progress.update(
                task,
                completed=completed,
                description=f"[cyan]Syncing: {in_progress} active | {completed}/{total_chats} done | {failed} failed | {total_messages:,} msgs"
            )

            # Show newly completed chats
            if completed > completed_previous:
                checkpoints = status.get('checkpoints', [])
                for cp in checkpoints:
                    if cp.get('status') == 'completed':
                        chat_jid = cp.get('chat_jid', 'unknown')
                        msgs_synced = cp.get('messages_synced', 0)
                        if msgs_synced > 0:  # Only show if actually synced messages
                            console.print(f"  [green]✓[/green] {chat_jid[:40]}: +{msgs_synced} messages")

            completed_previous = completed

            # Check if all done
            if completed + failed >= total_chats:
                break

            time.sleep(POLL_INTERVAL)

    return status


def display_chat_table(chats: List[Dict], limit: int = 10):
    """Display chat information in a formatted table."""
    table = Table(title=f"Top {limit} Chats by Oldest Message")

    table.add_column("Chat", style="cyan", no_wrap=True, width=35)
    table.add_column("Type", style="magenta")
    table.add_column("Messages", justify="right", style="green")
    table.add_column("Oldest", justify="center", style="yellow")
    table.add_column("Newest", justify="center", style="yellow")

    for chat in chats[:limit]:
        chat_type = "Group" if chat['is_group'] else "1-on-1"
        chat_display = chat['chat_jid'][:32] + "..." if len(chat['chat_jid']) > 35 else chat['chat_jid']

        table.add_row(
            chat_display,
            chat_type,
            f"{chat['message_count']:,}",
            str(chat['oldest_year']),
            str(chat['newest_year'])
        )

    console.print(table)
    console.print()


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description="Fetch deep WhatsApp message history using bulk sync")
    parser.add_argument('--yes', '-y', action='store_true', help="Skip confirmation prompt")
    parser.add_argument('--limit', type=int, default=None, help="Limit number of chats to process")
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE, help=f"Chats per bulk request (default: {BATCH_SIZE})")
    parser.add_argument('--max-messages', type=int, default=MAX_MESSAGES_PER_CHAT, help=f"Max messages per chat (default: {MAX_MESSAGES_PER_CHAT})")
    args = parser.parse_args()

    print_header()

    # Check Baileys bridge
    console.print("[cyan]🔍 Checking Baileys bridge status...[/cyan]")
    if not check_baileys_health():
        console.print("[red]✗ Baileys bridge is not running or not connected to WhatsApp[/red]")
        console.print("[yellow]Start it with:[/yellow] cd baileys-bridge && npm run dev")
        return 1

    console.print("[green]✓ Baileys bridge is connected and ready[/green]")
    console.print()

    # Get chats
    chats = get_chats_to_sync(limit=args.limit)
    console.print(f"[green]✓ Found {len(chats)} chats with messages[/green]")
    console.print()

    # Display chat summary
    display_chat_table(chats)

    if len(chats) > 10:
        console.print(f"[dim]... and {len(chats) - 10} more chats[/dim]")
        console.print()

    # Show sync plan
    num_batches = (len(chats) + args.batch_size - 1) // args.batch_size
    console.print(Panel(
        f"[bold]Sync Plan[/bold]\n\n"
        f"• Chats to sync: [cyan]{len(chats)}[/cyan]\n"
        f"• Batch size: [cyan]{args.batch_size}[/cyan] chats per request\n"
        f"• Batches: [cyan]{num_batches}[/cyan]\n"
        f"• Max messages per chat: [cyan]{args.max_messages:,}[/cyan]\n"
        f"• Estimated time: [cyan]{len(chats) * 15 // 60}[/cyan] minutes (at ~15s per chat)",
        border_style="blue"
    ))
    console.print()

    # Confirm
    if not args.yes:
        response = console.input("[bold yellow]Start bulk deep history sync? (y/N):[/bold yellow] ")
        if response.lower() != 'y':
            console.print("[yellow]Cancelled by user[/yellow]")
            return 0
    else:
        console.print("[cyan]Auto-confirmed with --yes flag[/cyan]")
        console.print()

    # Process in batches
    console.print(f"[bold cyan]Starting bulk sync in {num_batches} batches...[/bold cyan]")
    console.print()

    total_synced = 0
    total_failed = 0
    failed_chats = []

    for batch_num in range(num_batches):
        start_idx = batch_num * args.batch_size
        end_idx = min(start_idx + args.batch_size, len(chats))
        batch_chats = chats[start_idx:end_idx]
        batch_jids = [c['chat_jid'] for c in batch_chats]

        console.print(f"[bold]Batch {batch_num + 1}/{num_batches}[/bold] ({len(batch_jids)} chats)")
        console.print()

        # Start bulk sync
        result = start_bulk_sync(batch_jids, args.max_messages)

        if not result:
            console.print(f"[red]✗ Failed to start batch {batch_num + 1}[/red]")
            failed_chats.extend(batch_jids)
            total_failed += len(batch_jids)
            continue

        # Extract sync_ids from result (these are the chat_jids that were successfully queued)
        sync_ids = result.get('sync_ids', [])
        queued = result.get('queued', 0)
        console.print(f"[green]✓ Queued {queued} chats for sync[/green]")
        console.print()

        # Monitor progress using the sync_ids returned from the API
        final_status = monitor_bulk_sync(sync_ids, len(sync_ids))

        if final_status:
            batch_completed = final_status.get('completed', 0)
            batch_failed = final_status.get('failed', 0)
            batch_messages = final_status.get('total_messages_synced', 0)

            total_synced += batch_completed
            total_failed += batch_failed

            console.print()
            console.print(f"[green]✓ Batch {batch_num + 1} complete: {batch_completed} synced, {batch_failed} failed, {batch_messages:,} messages[/green]")
            console.print()

            # Track failed chats for retry
            if batch_failed > 0:
                checkpoints = final_status.get('checkpoints', [])
                for cp in checkpoints:
                    if cp.get('status') == 'failed':
                        failed_chats.append(cp.get('chat_jid'))

        # Small delay between batches
        if batch_num < num_batches - 1:
            console.print("[dim]Waiting 5 seconds before next batch...[/dim]")
            time.sleep(5)
            console.print()

    # Final summary
    console.print()
    console.print(Panel.fit(
        f"[bold green]Bulk Sync Complete![/bold green]\n\n"
        f"• Total chats processed: [cyan]{len(chats)}[/cyan]\n"
        f"• Successfully synced: [green]{total_synced}[/green]\n"
        f"• Failed: [red]{total_failed}[/red]\n"
        f"• Sync rate: [cyan]{total_synced * 100 // len(chats) if len(chats) > 0 else 0}%[/cyan]",
        border_style="green"
    ))
    console.print()

    # Show failed chats
    if failed_chats:
        console.print(f"[yellow]⚠️  {len(failed_chats)} chats failed to sync:[/yellow]")
        for jid in failed_chats[:10]:
            console.print(f"  • {jid}")
        if len(failed_chats) > 10:
            console.print(f"  ... and {len(failed_chats) - 10} more")
        console.print()
        console.print("[cyan]💡 Check Baileys logs for error details:[/cyan]")
        console.print("[dim]   tail -f /tmp/baileys-final-test.log[/dim]")
        console.print()

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]⚠️  Interrupted by user[/yellow]")
        exit(130)
