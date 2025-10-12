# Feature Specification: Comprehensive Test Coverage for WhatsApp MCP Server

**Feature Branch**: `001-add-comprehensive-test`
**Created**: 2025-10-12
**Status**: Draft
**Input**: User description: "Add comprehensive test coverage for WhatsApp MCP server. Need to: 1) Add unit tests for routing.py (341 lines, 0% coverage → 80% target), 2) Add unit tests for sync.py database synchronization logic, 3) Add unit tests for backends/health.py monitoring, 4) Add integration tests for hybrid workflows (mark_community_as_read_with_history end-to-end), 5) Add integration tests for backend failover scenarios, 6) Add integration tests for concurrent operations. Target: increase coverage from 20% to 70-80%."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Routing Logic Validation (Priority: P1)

As a **developer maintaining the WhatsApp MCP server**, I need comprehensive unit tests for the routing logic so that I can confidently make changes to backend selection algorithms without breaking production request routing.

**Why this priority**: Routing logic (`routing.py`) is the critical path for ALL requests. A bug in routing means complete system failure or requests going to wrong/unavailable backends. Currently has 0% coverage with 341 lines of complex conditional logic.

**Independent Test**: Can be fully tested by creating mock health monitors and backend clients, exercising all routing strategies (PREFER_GO, PREFER_BAILEYS, ROUND_ROBIN, FASTEST, PRIMARY_ONLY) with different backend availability scenarios, and verifying correct backend selection.

**Acceptance Scenarios**:

1. **Given** Go backend is healthy and Baileys is down, **When** a SEND_MESSAGE operation is routed, **Then** Go backend is selected
2. **Given** both backends are healthy, **When** a SYNC_FULL_HISTORY operation is routed, **Then** Baileys backend is selected (per PREFER_BAILEYS strategy)
3. **Given** primary backend fails mid-request, **When** route_with_fallback is called, **Then** request automatically retries on secondary backend
4. **Given** both backends are unhealthy, **When** any operation is routed, **Then** routing returns None and logs appropriate error
5. **Given** ROUND_ROBIN strategy is used, **When** multiple operations are routed, **Then** backends alternate in round-robin fashion
6. **Given** FASTEST strategy is enabled, **When** both backends are available, **Then** backend with lower response time is selected
7. **Given** a required backend is specified, **When** that backend is unavailable, **Then** routing returns None without attempting fallback

---

### User Story 2 - Database Synchronization Reliability (Priority: P2)

As a **system administrator deploying the WhatsApp MCP**, I need verified database synchronization logic so that historical message syncing between Baileys and Go doesn't result in data loss, corruption, or duplicates.

**Why this priority**: Database sync (`sync.py`) handles critical data migration from Baileys temp database to Go permanent storage. Bugs could cause message loss (unacceptable) or duplicate messages (degrades user experience). Currently minimal coverage for 410 lines of batch processing and deduplication logic.

**Independent Test**: Can be fully tested with mock HTTP responses from both backends, simulating various sync scenarios (empty chats, large batches, duplicates, network failures), and verifying correct deduplication, batch insertion, and checkpoint updates.

**Acceptance Scenarios**:

1. **Given** Baileys temp DB has 1000 new messages, **When** sync is triggered, **Then** all 1000 messages are inserted to Go DB with no duplicates
2. **Given** Baileys temp DB has 500 messages where 200 already exist in Go DB, **When** sync is triggered, **Then** only 300 new messages are inserted (deduplication works)
3. **Given** sync is processing a large batch, **When** Go DB insert fails midway, **Then** sync reports partial success with accurate count of synced messages
4. **Given** sync completes successfully, **When** checking Go DB, **Then** checkpoint is updated with correct message count
5. **Given** sync completes successfully, **When** checking Baileys temp DB, **Then** temp data is cleared to free space
6. **Given** sync processes 10,000 messages, **When** measuring throughput, **Then** sync achieves 100+ messages per second
7. **Given** network timeout occurs fetching from Baileys, **When** sync is attempted, **Then** sync fails gracefully and reports error without data corruption

---

### User Story 3 - Health Monitoring Accuracy (Priority: P3)

As a **DevOps engineer monitoring the WhatsApp MCP deployment**, I need accurate health checks for both backend bridges so that routing decisions are based on real-time backend availability and the system can handle partial outages gracefully.

**Why this priority**: Health monitoring (`backends/health.py`) determines which backends receive traffic. Incorrect health status causes requests to fail or overload a single backend. Currently limited coverage for 391 lines including timeout handling, connection errors, and health aggregation.

**Independent Test**: Can be fully tested with mock HTTP requests to backend health endpoints, simulating various response scenarios (healthy, degraded, timeout, connection refused, partial outage), and verifying correct health status classification.

**Acceptance Scenarios**:

1. **Given** Go backend returns HTTP 200 with "status: ok", **When** health check runs, **Then** Go backend is marked as "ok" with response time recorded
2. **Given** Baileys backend times out after 5 seconds, **When** health check runs, **Then** Baileys is marked as "unreachable" with timeout error
3. **Given** Go backend returns HTTP 500, **When** health check runs, **Then** Go is marked as "error" with HTTP status code logged
4. **Given** both backends are healthy, **When** overall health is checked, **Then** overall status is "ok" with both backends in available list
5. **Given** only Go backend is healthy, **When** overall health is checked, **Then** overall status is "degraded" with only Go in available list
6. **Given** both backends are unhealthy, **When** overall health is checked, **Then** overall status is "error" with empty available list
7. **Given** Baileys connection is refused (port closed), **When** health check runs, **Then** Baileys is marked "unreachable" within 1 second (no long timeout)
8. **Given** health check succeeds after previous failures, **When** failure count is checked, **Then** failure counter is reset to 0

---

### User Story 4 - Hybrid Workflow Integration (Priority: P4)

As a **QA engineer validating new releases**, I need end-to-end integration tests for complex hybrid workflows so that multi-step operations like `mark_community_as_read_with_history` work correctly across both backends.

**Why this priority**: Hybrid workflows combine Baileys (history sync) + orchestration layer (sync) + Go (mark as read) in complex multi-step sequences. Unit tests alone can't catch integration issues between components. Integration tests provide confidence in production behavior.

**Independent Test**: Can be fully tested with test instances of both Go and Baileys bridges running, executing complete `mark_community_as_read_with_history` workflow, and verifying each step completes successfully with expected side effects (messages synced, marked as read, temp DB cleared).

**Acceptance Scenarios**:

1. **Given** a community with 3 groups and 500 total unread messages, **When** mark_community_as_read_with_history is called, **Then** all 500 messages are retrieved from Baileys, synced to Go, and marked as read
2. **Given** history sync takes 2 minutes, **When** mark_community_as_read_with_history is called with 5-minute timeout, **Then** workflow completes successfully without timeout
3. **Given** Baileys history sync fails midway, **When** mark_community_as_read_with_history is called, **Then** workflow returns error with clear failure reason and no partial data corruption
4. **Given** Go mark-as-read fails after sync, **When** mark_community_as_read_with_history is called, **Then** workflow reports partial success with messages synced but not marked as read
5. **Given** concurrent mark_community_as_read_with_history calls for different communities, **When** both execute simultaneously, **Then** both complete successfully without race conditions

---

### User Story 5 - Backend Failover Resilience (Priority: P5)

As a **site reliability engineer**, I need integration tests simulating backend failures so that the system gracefully handles partial outages and automatically fails over to available backends.

**Why this priority**: Production systems must handle failures gracefully. Testing failover scenarios ensures the system remains available even when one backend crashes or becomes unreachable. These scenarios are difficult to unit test and require integration testing.

**Independent Test**: Can be fully tested by starting both backends, simulating failures (killing process, blocking port, introducing latency), triggering operations, and verifying automatic failover to healthy backend with no data loss.

**Acceptance Scenarios**:

1. **Given** Go backend is killed mid-request, **When** a message is sent, **Then** request automatically fails over to Baileys backend
2. **Given** Baileys backend becomes unreachable, **When** operations requiring Baileys are attempted, **Then** system returns clear error message without hanging
3. **Given** both backends fail simultaneously, **When** any operation is attempted, **Then** request fails immediately with "No backend available" error
4. **Given** Go backend recovers after failure, **When** next health check runs, **Then** Go is marked healthy and starts receiving traffic again
5. **Given** Baileys has 10-second response time, **When** using FASTEST routing strategy, **Then** Go backend is consistently selected over slow Baileys

---

### User Story 6 - Concurrent Operation Safety (Priority: P6)

As a **performance engineer**, I need integration tests with concurrent operations so that the system handles multiple simultaneous requests without race conditions, deadlocks, or resource exhaustion.

**Why this priority**: Production MCP servers handle multiple concurrent Claude requests. Concurrency bugs (race conditions, deadlocks) only appear under load and can cause data corruption or system hangs. Load testing ensures scalability.

**Independent Test**: Can be fully tested by spawning multiple threads/processes executing different operations simultaneously (sends, syncs, health checks), monitoring for errors/deadlocks, and verifying all operations complete successfully with correct results.

**Acceptance Scenarios**:

1. **Given** 10 concurrent message send operations, **When** all execute simultaneously, **Then** all 10 messages are sent successfully without conflicts
2. **Given** 5 concurrent database sync operations for different chats, **When** all execute simultaneously, **Then** all syncs complete without deadlocks or duplicate messages
3. **Given** 20 concurrent health checks, **When** all execute simultaneously, **Then** health checks complete in under 10 seconds without resource exhaustion
4. **Given** concurrent route_with_fallback calls during backend failure, **When** all execute simultaneously, **Then** all requests fail over correctly without race conditions
5. **Given** 100 concurrent operations mixed (send, sync, health), **When** system is under load, **Then** no operations fail due to concurrency issues and all complete within reasonable time

---

### Edge Cases

- What happens when routing logic receives an unknown operation type not in the operation_strategies map?
- How does deduplication handle messages with identical timestamps but different message IDs?
- What happens when health check times out but backend eventually responds (race condition)?
- How does sync handle empty Baileys temp DB (no messages to sync)?
- What happens when checkpoint update fails but message insertion succeeds?
- How does the system handle extremely large batches (100,000+ messages) in single sync?
- What happens when both backends report "degraded" status simultaneously?
- How does concurrent sync handle overlapping chat_jids (two threads syncing same chat)?
- What happens when Baileys temp DB clear fails after successful sync?
- How does routing handle partial backend recovery (WhatsApp connected but database down)?

## Requirements *(mandatory)*

### Functional Requirements

#### Routing Tests (routing.py - 341 lines, 0% → 80% coverage)

- **FR-001**: System MUST test all 5 routing strategies (PRIMARY_ONLY, PREFER_GO, PREFER_BAILEYS, ROUND_ROBIN, FASTEST) with mock health data
- **FR-002**: System MUST test backend selection for each operation type defined in OperationType enum (15+ operation types)
- **FR-003**: System MUST test fallback behavior when primary backend fails mid-request
- **FR-004**: System MUST test routing behavior when both backends are unavailable
- **FR-005**: System MUST test routing behavior when required backend is specified but unavailable
- **FR-006**: System MUST test round-robin counter increments correctly across multiple requests
- **FR-007**: System MUST test FASTEST strategy selects backend with lower response time
- **FR-008**: System MUST test error handling when invalid backend name is provided
- **FR-009**: System MUST test get_routing_info returns accurate routing configuration
- **FR-010**: System MUST test is_operation_available correctly indicates backend availability

#### Database Sync Tests (sync.py - 410 lines)

- **FR-011**: System MUST test sync_messages with various message batch sizes (0, 1, 100, 1000, 10000 messages)
- **FR-012**: System MUST test deduplication correctly identifies existing messages by composite key (chat_jid, timestamp, message_id)
- **FR-013**: System MUST test batch insertion to Go database with simulated network failures
- **FR-014**: System MUST test checkpoint update after successful sync
- **FR-015**: System MUST test Baileys temp DB clearing after sync completion
- **FR-016**: System MUST test sync achieves target throughput of 100+ messages/second
- **FR-017**: System MUST test sync handles empty Baileys temp DB gracefully
- **FR-018**: System MUST test sync_all_chats processes multiple chats sequentially
- **FR-019**: System MUST test error handling when Go database insert fails
- **FR-020**: System MUST test SyncResult contains accurate metrics (synced count, deduplicated count, elapsed time)

#### Health Monitoring Tests (backends/health.py - 391 lines)

- **FR-021**: System MUST test check_go_health handles HTTP 200 OK response correctly
- **FR-022**: System MUST test check_go_health handles connection timeout (5s timeout exceeded)
- **FR-023**: System MUST test check_go_health handles connection refused (backend down)
- **FR-024**: System MUST test check_go_health handles HTTP 500 error response
- **FR-025**: System MUST test check_baileys_health with same scenarios as Go health
- **FR-026**: System MUST test check_all aggregates health from both backends correctly
- **FR-027**: System MUST test overall status is "ok" when both backends healthy, "degraded" when one down, "error" when both down
- **FR-028**: System MUST test primary backend selection prefers Go over Baileys when both available
- **FR-029**: System MUST test failure counter resets on successful health check
- **FR-030**: System MUST test wait_for_backend polls until backend becomes available or timeout

#### Integration Tests - Hybrid Workflows

- **FR-031**: System MUST test mark_community_as_read_with_history completes end-to-end with real backend instances
- **FR-032**: System MUST test workflow handles Baileys history sync failure gracefully
- **FR-033**: System MUST test workflow handles Go mark-as-read failure after sync
- **FR-034**: System MUST test workflow respects timeout parameter (default 600s)
- **FR-035**: System MUST test workflow reports accurate metrics (messages synced, groups processed, elapsed time)

#### Integration Tests - Backend Failover

- **FR-036**: System MUST test automatic failover when primary backend becomes unreachable mid-operation
- **FR-037**: System MUST test system behavior when both backends fail simultaneously
- **FR-038**: System MUST test backend recovery detection and traffic restoration
- **FR-039**: System MUST test operations fail fast (under 10s) when no backends available
- **FR-040**: System MUST test FASTEST strategy switches to faster backend when response times change

#### Integration Tests - Concurrent Operations

- **FR-041**: System MUST test 10 concurrent message send operations complete without errors
- **FR-042**: System MUST test 5 concurrent database sync operations for different chats complete without deadlocks
- **FR-043**: System MUST test 20 concurrent health checks complete within reasonable time (under 10s total)
- **FR-044**: System MUST test concurrent route_with_fallback calls handle failover correctly without race conditions
- **FR-045**: System MUST test 100 mixed concurrent operations (send, sync, health) complete successfully under load

### Key Entities

- **Test Suite**: Collection of unit tests for a specific module (routing, sync, or health)
  - Module under test (routing.py, sync.py, health.py)
  - Number of test cases
  - Code coverage percentage
  - Execution time

- **Mock Backend**: Simulated Go/Baileys bridge for unit testing
  - Configurable health status responses
  - Simulated response times
  - Error injection capabilities

- **Integration Test Scenario**: End-to-end test case involving real backend instances
  - Preconditions (backend states)
  - Test actions (API calls, failures)
  - Expected outcomes (messages synced, failover occurred)
  - Cleanup steps

- **Coverage Report**: Test coverage metrics for the codebase
  - Overall coverage percentage
  - Per-module coverage breakdown
  - Uncovered lines report
  - Branch coverage statistics

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Code coverage increases from current 20% to minimum 70% overall (target: 75-80%)
- **SC-002**: routing.py achieves minimum 80% line coverage (currently 0%, 341 lines)
- **SC-003**: sync.py achieves minimum 75% line coverage (currently minimal, 410 lines)
- **SC-004**: backends/health.py achieves minimum 75% line coverage (currently minimal, 391 lines)
- **SC-005**: All unit tests execute in under 30 seconds total (fast feedback loop)
- **SC-006**: All integration tests execute in under 5 minutes total (acceptable CI/CD time)
- **SC-007**: Zero test failures in continuous integration pipeline after test implementation
- **SC-008**: 100% of critical paths (routing selection, sync deduplication, health aggregation) are covered by tests
- **SC-009**: Test suite detects at least 1 regression when intentionally introduced (validates test effectiveness)
- **SC-010**: Developers can run full test suite locally with single command (usability)
- **SC-011**: Integration tests successfully demonstrate failover within 5 seconds of backend failure
- **SC-012**: Concurrent operation tests demonstrate system handles 100 simultaneous operations without errors
- **SC-013**: Test documentation exists explaining how to run tests, interpret results, and add new tests
- **SC-014**: All edge cases documented in spec have corresponding test coverage

## Assumptions

- **AS-001**: Both Go and Baileys bridges have `/health` endpoints that return JSON status
- **AS-002**: Go bridge will implement `/messages/batch` endpoint for bulk message insertion (if not exists)
- **AS-003**: Baileys bridge will implement endpoints for fetching messages and clearing temp DB (if not exists)
- **AS-004**: Test environment can run both bridges on localhost ports 8080 and 8081 for integration tests
- **AS-005**: Standard Python testing frameworks (pytest, unittest, mock) are acceptable for implementation
- **AS-006**: Coverage measurement uses industry-standard tools (coverage.py, pytest-cov)
- **AS-007**: Integration tests can safely create/delete test data without affecting production databases
- **AS-008**: Concurrent operation tests can use threading/multiprocessing without hitting system limits
- **AS-009**: Mock HTTP libraries (requests-mock, responses) are acceptable for simulating backend responses
- **AS-010**: Test execution environment has sufficient resources (CPU, memory) for 100 concurrent operations

## Scope

### In Scope

- Unit tests for routing.py covering all routing strategies and operation types
- Unit tests for sync.py covering batch processing, deduplication, and error handling
- Unit tests for backends/health.py covering all health check scenarios and status aggregation
- Integration tests for mark_community_as_read_with_history workflow
- Integration tests for backend failover scenarios (single backend down, both down, recovery)
- Integration tests for concurrent operations (10-100 simultaneous operations)
- Test fixtures and mocks for simulating backend responses
- Test documentation explaining execution and interpretation
- Coverage reporting integration with CI/CD pipeline

### Out of Scope

- Performance benchmarking beyond basic throughput verification (100 msg/s target)
- Load testing beyond 100 concurrent operations (dedicated performance testing out of scope)
- Testing of Go bridge internal implementation (separate codebase)
- Testing of Baileys bridge internal implementation (separate codebase)
- UI/end-user acceptance testing (no UI in MCP server)
- Security penetration testing (separate security audit)
- Compliance testing (GDPR, etc.)
- Testing of MCP protocol implementation itself (assume protocol library works)
- Testing of WhatsApp API reliability (external dependency)

## Dependencies

- **DEP-001**: Go bridge must be running on localhost:8080 for integration tests
- **DEP-002**: Baileys bridge must be running on localhost:8081 for integration tests
- **DEP-003**: Test environment needs Python 3.12+ with pytest, pytest-cov, requests-mock installed
- **DEP-004**: Coverage reporting requires coverage.py or pytest-cov
- **DEP-005**: Integration tests need write access to test databases (or test mode in bridges)
- **DEP-006**: Concurrent operation tests need sufficient system resources (4+ CPU cores recommended)
- **DEP-007**: CI/CD pipeline must support running both backend bridges for integration tests

## Non-Functional Requirements

- **NFR-001**: Unit tests MUST NOT require external services (use mocks/stubs)
- **NFR-002**: Integration tests MUST clean up all test data after execution
- **NFR-003**: Test suite MUST be deterministic (no flaky tests due to timing/randomness)
- **NFR-004**: Test code MUST follow same coding standards as production code (linting, formatting)
- **NFR-005**: Test names MUST clearly describe scenario being tested (e.g., test_routing_prefers_go_when_both_healthy)
- **NFR-006**: Test failures MUST provide clear error messages indicating what failed and why
- **NFR-007**: Integration tests MUST have configurable timeouts to prevent hanging CI/CD pipelines
- **NFR-008**: Concurrent tests MUST use proper synchronization to avoid race conditions in test code itself
- **NFR-009**: Mock objects MUST accurately simulate real backend behavior (avoid testing against unrealistic mocks)
- **NFR-010**: Coverage reports MUST exclude test files themselves from coverage calculations
