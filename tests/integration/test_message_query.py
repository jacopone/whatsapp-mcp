"""
Integration test for message query endpoints (T026).

Tests the full flow of querying synced messages from the Go database:
1. Check backend health
2. Get message statistics
3. Query messages with various filters
4. Test pagination
"""
import sys
import time
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "unified-mcp"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "unified-mcp" / "backends"))

import go_client


def test_backend_health():
    """Test 1: Verify Go backend is healthy."""
    print("\n" + "=" * 80)
    print("TEST 1: Backend Health Check")
    print("=" * 80)

    healthy = go_client.health_check()
    print(f"✅ Go backend healthy: {healthy}")

    if not healthy:
        print("❌ FAILED: Go backend is not healthy")
        print("   Make sure the Go backend is running on http://localhost:8080")
        return False

    return True


def test_message_statistics():
    """Test 2: Get message statistics."""
    print("\n" + "=" * 80)
    print("TEST 2: Get Message Statistics")
    print("=" * 80)

    stats = go_client.get_message_stats()

    if not stats.get("success"):
        print(f"❌ FAILED: {stats.get('message', 'Unknown error')}")
        return False

    print(f"✅ Statistics retrieved successfully:")
    print(f"   Total messages: {stats.get('total_messages', 0)}")
    print(f"   Total chats: {stats.get('total_chats', 0)}")
    print(f"   Total contacts: {stats.get('total_contacts', 0)}")
    print(f"   Media messages: {stats.get('media_messages', 0)}")
    print(f"   Text messages: {stats.get('text_messages', 0)}")

    if stats.get('messages_by_type'):
        print(f"   Messages by type:")
        for media_type, count in stats['messages_by_type'].items():
            print(f"     - {media_type}: {count}")

    if stats.get('oldest_message'):
        print(f"   Oldest message: {stats['oldest_message']}")
    if stats.get('newest_message'):
        print(f"   Newest message: {stats['newest_message']}")

    return True


def test_query_all_messages():
    """Test 3: Query all messages with default limit."""
    print("\n" + "=" * 80)
    print("TEST 3: Query All Messages (Default Limit)")
    print("=" * 80)

    result = go_client.query_messages(limit=20)

    if not result.get("success"):
        print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
        return False

    messages = result.get("messages", [])
    total = result.get("total", 0)

    print(f"✅ Query successful:")
    print(f"   Total matching messages: {total}")
    print(f"   Returned messages: {len(messages)}")
    print(f"   Limit: {result.get('limit', 0)}")
    print(f"   Offset: {result.get('offset', 0)}")

    if messages:
        print(f"\n   Sample messages:")
        for i, msg in enumerate(messages[:3]):
            print(f"   [{i+1}] {msg.get('timestamp')}: {msg.get('sender_name', 'Unknown')} -> {msg.get('content', '(media)')[:50]}")

    return True


def test_query_by_chat():
    """Test 4: Query messages from a specific chat."""
    print("\n" + "=" * 80)
    print("TEST 4: Query Messages by Chat")
    print("=" * 80)

    # First, get a chat JID from available messages
    result = go_client.query_messages(limit=1)

    if not result.get("success") or not result.get("messages"):
        print("⚠️  SKIPPED: No messages available to test with")
        return True

    chat_jid = result["messages"][0].get("chat_jid")
    print(f"   Testing with chat: {chat_jid}")

    # Query messages from this specific chat
    result = go_client.query_messages(chat_jid=chat_jid, limit=10)

    if not result.get("success"):
        print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
        return False

    messages = result.get("messages", [])
    total = result.get("total", 0)

    print(f"✅ Query successful:")
    print(f"   Total messages in chat: {total}")
    print(f"   Returned messages: {len(messages)}")

    # Verify all messages are from the same chat
    all_from_same_chat = all(msg.get("chat_jid") == chat_jid for msg in messages)
    if all_from_same_chat:
        print(f"   ✅ All messages from correct chat")
    else:
        print(f"   ❌ Some messages from different chat")
        return False

    return True


def test_query_by_content():
    """Test 5: Search messages by content."""
    print("\n" + "=" * 80)
    print("TEST 5: Search Messages by Content")
    print("=" * 80)

    # Search for a common word (you might want to change this based on your data)
    search_term = "the"

    result = go_client.query_messages(content=search_term, limit=10)

    if not result.get("success"):
        print(f"❌ FAILED: {result.get('message', 'Unknown error')}")
        return False

    messages = result.get("messages", [])
    total = result.get("total", 0)

    print(f"✅ Search successful:")
    print(f"   Search term: '{search_term}'")
    print(f"   Total matching messages: {total}")
    print(f"   Returned messages: {len(messages)}")

    if messages:
        print(f"\n   Sample matches:")
        for i, msg in enumerate(messages[:3]):
            content = msg.get('content', '')
            print(f"   [{i+1}] {content[:80]}...")

    return True


def test_pagination():
    """Test 6: Test pagination with offset and limit."""
    print("\n" + "=" * 80)
    print("TEST 6: Test Pagination")
    print("=" * 80)

    # Get first page
    page1 = go_client.query_messages(limit=5, offset=0)

    if not page1.get("success"):
        print(f"❌ FAILED: {page1.get('message', 'Unknown error')}")
        return False

    # Get second page
    page2 = go_client.query_messages(limit=5, offset=5)

    if not page2.get("success"):
        print(f"❌ FAILED: {page2.get('message', 'Unknown error')}")
        return False

    page1_messages = page1.get("messages", [])
    page2_messages = page2.get("messages", [])

    print(f"✅ Pagination successful:")
    print(f"   Page 1 (offset=0, limit=5): {len(page1_messages)} messages")
    print(f"   Page 2 (offset=5, limit=5): {len(page2_messages)} messages")
    print(f"   Total messages: {page1.get('total', 0)}")

    # Verify pages don't overlap
    if page1_messages and page2_messages:
        page1_ids = {msg.get("id") for msg in page1_messages}
        page2_ids = {msg.get("id") for msg in page2_messages}
        overlap = page1_ids & page2_ids

        if overlap:
            print(f"   ❌ Pages overlap! {len(overlap)} duplicate messages")
            return False
        else:
            print(f"   ✅ No overlap between pages")

    return True


def test_media_filtering():
    """Test 7: Filter messages by media type."""
    print("\n" + "=" * 80)
    print("TEST 7: Filter by Media Type")
    print("=" * 80)

    # Query with media included
    result_with_media = go_client.query_messages(include_media=True, limit=10)

    if not result_with_media.get("success"):
        print(f"❌ FAILED: {result_with_media.get('message', 'Unknown error')}")
        return False

    # Query without media (text only)
    result_text_only = go_client.query_messages(include_media=False, limit=10)

    if not result_text_only.get("success"):
        print(f"❌ FAILED: {result_text_only.get('message', 'Unknown error')}")
        return False

    print(f"✅ Media filtering successful:")
    print(f"   With media: {len(result_with_media.get('messages', []))} messages")
    print(f"   Text only: {len(result_text_only.get('messages', []))} messages")

    # Verify text-only messages have no media
    text_only_messages = result_text_only.get("messages", [])
    has_media = any(msg.get("media_type") for msg in text_only_messages)

    if has_media:
        print(f"   ❌ Text-only query returned messages with media")
        return False
    else:
        print(f"   ✅ Text-only filter working correctly")

    return True


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUITE: Message Query Endpoints (T026)")
    print("=" * 80)
    print("\nThis test suite validates:")
    print("  - T024: Go REST API endpoints for message queries")
    print("  - T025: Python MCP tools for message queries")
    print("  - Full end-to-end query functionality")

    tests = [
        ("Backend Health", test_backend_health),
        ("Message Statistics", test_message_statistics),
        ("Query All Messages", test_query_all_messages),
        ("Query by Chat", test_query_by_chat),
        ("Search by Content", test_query_by_content),
        ("Pagination", test_pagination),
        ("Media Filtering", test_media_filtering),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nPhase 3 (T024-T026) is complete:")
        print("  ✅ T024: Go REST API endpoints implemented")
        print("  ✅ T025: Python MCP tools implemented")
        print("  ✅ T026: Integration tests passing")
        return 0
    else:
        print(f"\n❌ {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
