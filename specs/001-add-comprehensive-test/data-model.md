# Data Model: Comprehensive Test Coverage

**Branch**: `001-add-comprehensive-test` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)

**Purpose**: Define the key entities, relationships, and data structures for the comprehensive test coverage system.

---

## Core Entities

### 1. Test Suite

A collection of test cases organized by module and test type.

**Attributes**:
- `module_name` (string): Module being tested (routing, sync, health, hybrid)
- `test_type` (enum): unit | integration | e2e
- `test_cases` (list[TestCase]): Individual test cases in the suite
- `coverage_percentage` (float): Line coverage for this module (0-100)
- `branch_coverage_percentage` (float): Branch coverage for this module (0-100)
- `execution_time_seconds` (float): Total time to run all tests in suite
- `status` (enum): passing | failing | skipped
- `last_run_timestamp` (datetime): When tests were last executed

**Invariants**:
- Unit test suites MUST complete in <30 seconds
- Integration test suites MUST complete in <5 minutes
- Coverage percentages are calculated by pytest-cov

**Example**:
```python
{
    "module_name": "routing",
    "test_type": "unit",
    "test_cases": [
        TestCase(name="test_routing_selects_go_backend_when_baileys_down", ...),
        TestCase(name="test_routing_prefers_baileys_for_sync_operations", ...),
    ],
    "coverage_percentage": 82.5,
    "branch_coverage_percentage": 78.3,
    "execution_time_seconds": 12.4,
    "status": "passing",
    "last_run_timestamp": "2025-10-12T14:30:00Z"
}
```

---

### 2. Test Case

An individual test scenario validating specific behavior.

**Attributes**:
- `name` (string): Descriptive test name (test_<feature>_<scenario>_<expected_result>)
- `file_path` (string): Relative path to test file
- `line_number` (int): Starting line in test file
- `test_type` (enum): unit | integration | e2e
- `markers` (list[string]): pytest markers (e.g., ["asyncio", "timeout(30)"])
- `fixtures_used` (list[string]): pytest fixtures required
- `duration_seconds` (float): Execution time for this test
- `status` (enum): passed | failed | skipped | xfail
- `failure_message` (string | null): Error message if failed
- `assertions_count` (int): Number of assertions in test
- `lines_covered` (list[int]): Source code lines covered by this test

**Invariants**:
- Test names MUST follow convention: `test_<feature>_<scenario>_<expected>`
- Each test MUST have at least one assertion
- Tests MUST clean up resources (handled by fixtures with yield)

**Example**:
```python
{
    "name": "test_routing_selects_go_backend_when_baileys_unavailable",
    "file_path": "tests/unit/test_routing.py",
    "line_number": 45,
    "test_type": "unit",
    "markers": ["asyncio"],
    "fixtures_used": ["mock_health_monitor", "sample_operations"],
    "duration_seconds": 0.12,
    "status": "passed",
    "failure_message": null,
    "assertions_count": 3,
    "lines_covered": [89, 90, 91, 95, 96, 102]
}
```

---

### 3. Mock Backend

Simulated Go/Baileys bridge for unit tests.

**Attributes**:
- `backend_type` (enum): go | baileys
- `base_url` (string): Mocked endpoint URL (e.g., "http://localhost:8080")
- `health_status` (enum): healthy | unhealthy | degraded | unreachable
- `response_delay_ms` (int): Simulated latency (0-5000)
- `error_injection_enabled` (bool): Whether to inject errors
- `error_types` (list[enum]): Types of errors to inject (timeout, 500, 503, connection_refused)
- `response_templates` (dict): Predefined responses for different endpoints
- `call_history` (list[dict]): Record of all calls made to this mock

**Invariants**:
- Mock backends MUST use responses library for HTTP mocking
- Mock backends MUST reset state between tests (automatic via responses.activate)
- Response delays MUST NOT exceed test timeout thresholds

**Example**:
```python
{
    "backend_type": "go",
    "base_url": "http://localhost:8080",
    "health_status": "healthy",
    "response_delay_ms": 50,
    "error_injection_enabled": false,
    "error_types": [],
    "response_templates": {
        "/health": {"status": "healthy", "uptime_seconds": 3600},
        "/v2/send_text_message": {"success": true, "message_id": "mock-123"}
    },
    "call_history": [
        {"endpoint": "/health", "timestamp": "2025-10-12T14:30:01Z", "response_code": 200}
    ]
}
```

---

### 4. Integration Test Scenario

End-to-end test scenario with real or Docker-based backends.

**Attributes**:
- `scenario_name` (string): Descriptive name (e.g., "mark_community_as_read_with_full_history_sync")
- `preconditions` (list[string]): Setup requirements
- `backends_required` (list[enum]): Which backends must be running (go, baileys, both)
- `test_data` (dict): Initial state (messages, chats, contacts)
- `actions` (list[dict]): Steps to perform (tool calls, verifications)
- `expected_outcomes` (list[dict]): Success criteria
- `cleanup_actions` (list[string]): Teardown steps
- `execution_time_seconds` (float): Total scenario runtime
- `docker_compose_file` (string | null): Path to docker-compose.yml if using containers

**Invariants**:
- Integration scenarios MUST clean up test data (messages, database rows)
- Integration scenarios MUST verify both backends are healthy before starting
- Integration scenarios MUST use deterministic test data (no random values)

**Example**:
```python
{
    "scenario_name": "hybrid_workflow_mark_community_as_read_with_history",
    "preconditions": [
        "Go bridge running on port 8080",
        "Baileys bridge running on port 8081",
        "Test database initialized with sample community"
    ],
    "backends_required": ["go", "baileys"],
    "test_data": {
        "community_jid": "120363143634035041@g.us",
        "groups": ["120363281234567890@g.us", "120363289876543210@g.us"],
        "unread_messages": 150
    },
    "actions": [
        {"action": "call_retrieve_full_history", "timeout": 300},
        {"action": "call_sync_history_to_database", "timeout": 60},
        {"action": "call_mark_community_as_read", "community_jid": "120363143634035041@g.us"}
    ],
    "expected_outcomes": [
        {"check": "all_messages_synced", "expected": 150},
        {"check": "all_messages_marked_read", "expected": 150},
        {"check": "no_errors_logged", "expected": true}
    ],
    "cleanup_actions": [
        "delete_test_messages",
        "reset_read_receipts",
        "clear_sync_checkpoints"
    ],
    "execution_time_seconds": 45.3,
    "docker_compose_file": "tests/integration/docker-compose.yml"
}
```

---

### 5. Coverage Report

Aggregated coverage metrics for the codebase.

**Attributes**:
- `overall_coverage_percentage` (float): Total line coverage across all modules
- `overall_branch_coverage_percentage` (float): Total branch coverage
- `module_coverage` (dict): Per-module breakdown
- `uncovered_lines` (dict): Lines not covered by any test
- `missing_branches` (dict): Conditional branches not tested
- `coverage_delta` (float): Change from previous run (+/- percentage points)
- `threshold_pass` (bool): Whether minimum threshold (70%) is met
- `generated_timestamp` (datetime): When report was generated
- `html_report_path` (string): Path to interactive HTML report

**Invariants**:
- Coverage MUST be measured with branch coverage enabled
- Coverage reports MUST exclude test files themselves
- Coverage MUST fail CI/CD if below 70% threshold

**Example**:
```python
{
    "overall_coverage_percentage": 73.5,
    "overall_branch_coverage_percentage": 68.2,
    "module_coverage": {
        "routing.py": {"line_coverage": 82.5, "branch_coverage": 78.3},
        "sync.py": {"line_coverage": 76.8, "branch_coverage": 72.1},
        "health.py": {"line_coverage": 79.4, "branch_coverage": 74.6}
    },
    "uncovered_lines": {
        "routing.py": [145, 146, 203, 204, 205],
        "sync.py": [89, 234, 235, 236, 312]
    },
    "missing_branches": {
        "routing.py": ["45->47 (else branch)", "102->105 (except clause)"],
        "sync.py": ["156->158 (if condition false)"]
    },
    "coverage_delta": +3.2,
    "threshold_pass": true,
    "generated_timestamp": "2025-10-12T14:35:22Z",
    "html_report_path": "htmlcov/index.html"
}
```

---

## Entity Relationships

```
Test Suite (1) ──────► (N) Test Case
    │
    │ measures
    ▼
Coverage Report
    │
    │ aggregates from
    ▼
Module Coverage
    │
    │ identifies
    ▼
Uncovered Lines


Test Case (N) ────────► (1) Mock Backend
    │                        (for unit tests)
    │
    │ uses
    ▼
Test Fixtures
    │
    │ provides
    ▼
Test Data


Integration Test Scenario (1) ──► (N) Real Backends
    │                                   (Go + Baileys)
    │
    │ requires
    ▼
Docker Compose Setup
```

---

## Test Data Schemas

### Sample Message

```python
{
    "id": "msg-12345",
    "chat_jid": "1234567890@s.whatsapp.net",
    "sender": "9876543210@s.whatsapp.net",
    "content": "Test message content",
    "timestamp": 1728745200,
    "is_from_me": false,
    "read_status": false,
    "media_type": null
}
```

### Sample Health Response

```python
{
    "status": "healthy",
    "uptime_seconds": 3600,
    "requests_handled": 1250,
    "active_connections": 5,
    "last_error": null,
    "backend_version": "1.0.0"
}
```

### Sample Sync Checkpoint

```python
{
    "chat_jid": "120363143634035041@g.us",
    "last_synced_message_id": "msg-99999",
    "last_synced_timestamp": 1728745200,
    "messages_synced_count": 1500,
    "sync_in_progress": false,
    "last_sync_error": null
}
```

---

## Concurrency Data Structures

### Thread Execution Record

```python
{
    "thread_id": 5,
    "operation": "mark_chat_as_read",
    "chat_jid": "1234567890@s.whatsapp.net",
    "start_time": "2025-10-12T14:30:00.123Z",
    "end_time": "2025-10-12T14:30:02.456Z",
    "duration_ms": 2333,
    "result": "success",
    "error": null,
    "backend_used": "go"
}
```

### Race Condition Detection

```python
{
    "test_name": "test_concurrent_mark_as_read_same_chat",
    "thread_count": 10,
    "barrier_sync": true,
    "race_detected": false,
    "expected_final_state": {"read_count": 10},
    "actual_final_state": {"read_count": 10},
    "anomalies": []
}
```

---

## State Transitions

### Test Execution States

```
pending → running → passed
                  → failed
                  → skipped
                  → xfail (expected failure)
```

### Backend Health States

```
unknown → healthy ⇄ degraded
        → unhealthy
        → unreachable
```

### Sync States

```
idle → in_progress → completed
                   → failed
                   → cancelled
```

---

## Validation Rules

1. **Coverage Thresholds**:
   - Overall: ≥70%
   - routing.py: ≥80%
   - sync.py: ≥75%
   - health.py: ≥75%

2. **Performance Constraints**:
   - Unit test suite: <30 seconds
   - Integration test suite: <5 minutes
   - Individual test: <10 seconds (with timeout marker)

3. **Test Isolation**:
   - Each test MUST be independent (no shared state)
   - Fixtures with `yield` MUST clean up resources
   - Database tests MUST use in-memory SQLite or cleanup data

4. **Determinism**:
   - No random test data (use fixed seeds or deterministic values)
   - No time-dependent tests (use frozen time or mocks)
   - No network-dependent tests in unit tests (use mocks)

---

**Data Model Complete**: 2025-10-12
**Ready for**: Contract generation (Phase 1 continuation)
