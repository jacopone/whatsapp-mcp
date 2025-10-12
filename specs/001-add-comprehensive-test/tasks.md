# Tasks: Comprehensive Test Coverage for WhatsApp MCP Server

**Input**: Design documents from `/specs/001-add-comprehensive-test/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: This feature IS EXPLICITLY ABOUT TESTING - all tasks are test-related.

**Organization**: Tasks are grouped by user story (routing, sync, health, hybrid workflows, failover, concurrency) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

## Path Conventions
- Base path: `whatsapp-mcp/unified-mcp/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Source: `routing.py`, `sync.py`, `backends/health.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test infrastructure initialization and basic configuration

- [X] T001 [P] Add pytest-cov>=6.0.0 to pyproject.toml dev dependencies
- [X] T002 [P] Add pytest-timeout>=2.2.0 to pyproject.toml dev dependencies
- [X] T003 [P] Add pytest-docker>=3.1.0 to pyproject.toml dev dependencies
- [X] T004 [P] Add responses>=0.25.0 to pyproject.toml dev dependencies
- [X] T005 [P] Add psutil>=5.9.0 to pyproject.toml dev dependencies
- [X] T006 Configure pytest in pyproject.toml (testpaths, asyncio_mode="auto", strict-markers, timeout=10)
- [X] T007 Configure coverage in pyproject.toml (branch=true, source=["."], omit=["*/tests/*"], fail_under=70, concurrency=["thread", "greenlet"])
- [X] T008 Create tests/ directory structure (unit/, integration/, e2e/, subdirs)
- [X] T009 Create tests/unit/backends/ directory for health tests
- [X] T010 Create tests/integration/backends/ directory for health integration tests
- [X] T011 Create empty .gitkeep files in all test directories

**Checkpoint**: Test infrastructure configured, ready for shared fixtures ✅

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared fixtures and test data that ALL test suites depend on

**⚠️ CRITICAL**: No user story testing can begin until this phase is complete

- [X] T012 [P] Create tests/conftest.py with sample_messages fixture (10+ messages, mixed read/unread)
- [X] T013 [P] Create tests/conftest.py with sample_chats fixture (3 direct, 2 group chats)
- [X] T014 [P] Create tests/conftest.py with sample_health_response fixture (healthy/degraded/unhealthy states)
- [X] T015 [P] Create tests/conftest.py with test_database fixture (in-memory SQLite with yield cleanup)
- [X] T016 Create tests/unit/conftest.py with mock_go_backend fixture using responses library
- [X] T017 Create tests/unit/conftest.py with mock_baileys_backend fixture using responses library
- [X] T018 Create tests/unit/conftest.py with mock_health_monitor fixture (integrates mock backends)
- [X] T019 [P] Create tests/unit/conftest.py with sample_operations fixture (list of operation types with expected backends)
- [X] T020 [P] Create tests/unit/conftest.py with mock_time fixture for deterministic time-dependent tests
- [X] T021 Create tests/integration/conftest.py with docker_services fixture using pytest-docker (session scope)
- [X] T022 Create tests/integration/docker-compose.yml defining go-backend and baileys-backend services
- [X] T023 Create tests/integration/conftest.py with integration_database fixture (test DB with cleanup)
- [X] T024 Create tests/integration/conftest.py with integration_test_data fixture (pre-populated messages/chats)
- [X] T025 Create tests/e2e/conftest.py with e2e_test_community fixture (community + 2 groups + 100 messages)
- [X] T026 Create tests/e2e/conftest.py with e2e_workflow_tracker fixture (tracks step timing and errors)

**Checkpoint**: Foundation ready - all user story tests can now run with shared fixtures

---

## Phase 3: User Story 1 - Routing Logic Validation (Priority: P1) 🎯 MVP

**Goal**: Achieve 80% coverage of routing.py (341 lines) with comprehensive unit tests for all routing strategies

**Independent Test**: Run `pytest tests/unit/test_routing.py --cov=routing --cov-report=term-missing` and verify ≥80% coverage

### Unit Tests for User Story 1

**NOTE: These tests validate critical routing path - must pass before any routing changes**

- [X] T027 [P] [US1] Test routing selects Go backend when Baileys is down in tests/unit/test_routing.py
- [X] T028 [P] [US1] Test routing selects Baileys backend when Go is down in tests/unit/test_routing.py
- [X] T029 [P] [US1] Test routing prefers Baileys for SYNC_FULL_HISTORY operation (PREFER_BAILEYS strategy) in tests/unit/test_routing.py
- [X] T030 [P] [US1] Test routing prefers Go for SEND_MESSAGE operation (PREFER_GO strategy) in tests/unit/test_routing.py
- [X] T031 [P] [US1] Test routing returns None when both backends are unavailable in tests/unit/test_routing.py
- [X] T032 [P] [US1] Test routing returns None when required backend is unavailable (no fallback) in tests/unit/test_routing.py
- [X] T033 [P] [US1] Test ROUND_ROBIN strategy alternates backends across multiple requests in tests/unit/test_routing.py
- [X] T034 [P] [US1] Test ROUND_ROBIN counter increments correctly in tests/unit/test_routing.py
- [X] T035 [P] [US1] Test FASTEST strategy selects backend with lower response time in tests/unit/test_routing.py
- [X] T036 [P] [US1] Test FASTEST strategy switches when response times change in tests/unit/test_routing.py
- [X] T037 [P] [US1] Test route_with_fallback retries on secondary backend when primary fails in tests/unit/test_routing.py
- [X] T038 [P] [US1] Test route_with_fallback returns None when both backends fail in tests/unit/test_routing.py
- [X] T039 [P] [US1] Test routing handles all 15+ operation types correctly in tests/unit/test_routing.py (parametrized)
- [X] T040 [P] [US1] Test routing handles unknown operation type gracefully in tests/unit/test_routing.py
- [X] T041 [P] [US1] Test routing handles invalid backend name error in tests/unit/test_routing.py
- [X] T042 [P] [US1] Test get_routing_info returns accurate routing configuration in tests/unit/test_routing.py
- [X] T043 [P] [US1] Test is_operation_available correctly indicates backend availability in tests/unit/test_routing.py
- [X] T044 [P] [US1] Test PRIMARY_ONLY strategy respects primary backend setting in tests/unit/test_routing.py
- [X] T045 [P] [US1] Test routing logs appropriate errors when backends unavailable in tests/unit/test_routing.py
- [X] T046 [P] [US1] Test routing with degraded backend (partial availability) in tests/unit/test_routing.py
- [X] T047 [P] [US1] Test routing handles concurrent requests without state corruption in tests/unit/test_routing.py

**Checkpoint**: At this point, routing.py should have 80%+ coverage and all routing scenarios tested

---

## Phase 4: User Story 2 - Database Synchronization Reliability (Priority: P2)

**Goal**: Achieve 75% coverage of sync.py (410 lines) with tests for batch processing, deduplication, and error handling

**Independent Test**: Run `pytest tests/unit/test_sync.py --cov=sync --cov-report=term-missing` and verify ≥75% coverage

### Unit Tests for User Story 2

- [X] T048 [P] [US2] Test sync_messages with 0 messages (empty Baileys DB) in tests/unit/test_sync.py
- [X] T049 [P] [US2] Test sync_messages with 1 message in tests/unit/test_sync.py
- [X] T050 [P] [US2] Test sync_messages with 100 messages batch in tests/unit/test_sync.py
- [X] T051 [P] [US2] Test sync_messages with 1000 messages batch in tests/unit/test_sync.py
- [X] T052 [P] [US2] Test sync_messages with 10000 messages batch (large batch handling) in tests/unit/test_sync.py
- [X] T053 [P] [US2] Test deduplication identifies existing messages by composite key (chat_jid, timestamp, message_id) in tests/unit/test_sync.py
- [X] T054 [P] [US2] Test deduplication handles messages with identical timestamps but different IDs in tests/unit/test_sync.py
- [X] T055 [P] [US2] Test sync with 500 messages where 200 exist (deduplication removes 200) in tests/unit/test_sync.py
- [X] T056 [P] [US2] Test batch insertion to Go database succeeds in tests/unit/test_sync.py
- [X] T057 [P] [US2] Test batch insertion failure midway reports partial success with accurate count in tests/unit/test_sync.py
- [X] T058 [P] [US2] Test network timeout fetching from Baileys fails gracefully without data corruption in tests/unit/test_sync.py
- [X] T059 [P] [US2] Test checkpoint update after successful sync contains correct message count in tests/unit/test_sync.py
- [X] T060 [P] [US2] Test checkpoint update failure is logged but doesn't block sync in tests/unit/test_sync.py
- [X] T061 [P] [US2] Test Baileys temp DB clearing after sync completion in tests/unit/test_sync.py
- [X] T062 [P] [US2] Test Baileys temp DB clear failure is logged but doesn't fail sync in tests/unit/test_sync.py
- [X] T063 [P] [US2] Test sync achieves 100+ messages/second throughput (performance validation) in tests/unit/test_sync.py
- [X] T064 [P] [US2] Test sync_all_chats processes multiple chats sequentially in tests/unit/test_sync.py
- [X] T065 [P] [US2] Test SyncResult contains accurate metrics (synced count, deduplicated count, elapsed time) in tests/unit/test_sync.py
- [X] T066 [P] [US2] Test sync handles Go database connection error gracefully in tests/unit/test_sync.py

**Checkpoint**: At this point, sync.py should have 75%+ coverage and all sync scenarios tested

---

## Phase 5: User Story 3 - Health Monitoring Accuracy (Priority: P3)

**Goal**: Achieve 75% coverage of backends/health.py (391 lines) with tests for health check scenarios and status aggregation

**Independent Test**: Run `pytest tests/unit/backends/test_health.py --cov=backends/health --cov-report=term-missing` and verify ≥75% coverage

### Unit Tests for User Story 3

- [X] T067 [P] [US3] Test check_go_health handles HTTP 200 OK response correctly in tests/unit/backends/test_health.py
- [X] T068 [P] [US3] Test check_go_health handles connection timeout (5s exceeded) in tests/unit/backends/test_health.py
- [X] T069 [P] [US3] Test check_go_health handles connection refused (backend down) in tests/unit/backends/test_health.py
- [X] T070 [P] [US3] Test check_go_health handles HTTP 500 error response in tests/unit/backends/test_health.py
- [X] T071 [P] [US3] Test check_go_health records response time accurately in tests/unit/backends/test_health.py
- [X] T072 [P] [US3] Test check_baileys_health handles HTTP 200 OK response in tests/unit/backends/test_health.py
- [X] T073 [P] [US3] Test check_baileys_health handles connection timeout in tests/unit/backends/test_health.py
- [X] T074 [P] [US3] Test check_baileys_health handles connection refused in tests/unit/backends/test_health.py
- [X] T075 [P] [US3] Test check_baileys_health handles HTTP 500 error in tests/unit/backends/test_health.py
- [X] T076 [P] [US3] Test check_all aggregates health when both backends healthy (overall status="ok") in tests/unit/backends/test_health.py
- [X] T077 [P] [US3] Test check_all aggregates health when only Go healthy (overall status="degraded") in tests/unit/backends/test_health.py
- [X] T078 [P] [US3] Test check_all aggregates health when only Baileys healthy (overall status="degraded") in tests/unit/backends/test_health.py
- [X] T079 [P] [US3] Test check_all aggregates health when both backends down (overall status="error", empty available list) in tests/unit/backends/test_health.py
- [X] T080 [P] [US3] Test primary backend selection prefers Go over Baileys when both available in tests/unit/backends/test_health.py
- [X] T081 [P] [US3] Test failure counter resets on successful health check in tests/unit/backends/test_health.py
- [X] T082 [P] [US3] Test failure counter increments on failed health check in tests/unit/backends/test_health.py
- [X] T083 [P] [US3] Test wait_for_backend polls until backend becomes available in tests/unit/backends/test_health.py
- [X] T084 [P] [US3] Test wait_for_backend times out if backend never becomes available in tests/unit/backends/test_health.py
- [X] T085 [P] [US3] Test health check handles both backends reporting "degraded" simultaneously in tests/unit/backends/test_health.py
- [X] T086 [P] [US3] Test health check handles partial backend recovery (connected but degraded) in tests/unit/backends/test_health.py
- [X] T087 [P] [US3] Test health check completes within 1 second when backend port closed (fast failure) in tests/unit/backends/test_health.py

**Checkpoint**: At this point, backends/health.py should have 75%+ coverage and all health scenarios tested

---

## Phase 6: User Story 4 - Hybrid Workflow Integration (Priority: P4)

**Goal**: Validate end-to-end hybrid workflows work correctly across both backends with integration tests

**Independent Test**: Run `pytest tests/e2e/test_hybrid_workflows.py -v` with both bridges running and verify all workflows complete successfully

### Integration Tests for User Story 4

- [X] T088 [P] [US4] Test mark_community_as_read_with_history completes end-to-end with 500 messages in tests/e2e/test_hybrid_workflows.py
- [X] T089 [P] [US4] Test mark_community_as_read_with_history respects 5-minute timeout (doesn't hang) in tests/e2e/test_hybrid_workflows.py
- [X] T090 [P] [US4] Test mark_community_as_read_with_history handles Baileys history sync failure gracefully in tests/e2e/test_hybrid_workflows.py
- [X] T091 [P] [US4] Test mark_community_as_read_with_history handles Go mark-as-read failure after sync in tests/e2e/test_hybrid_workflows.py
- [X] T092 [P] [US4] Test mark_community_as_read_with_history reports accurate metrics (synced count, groups processed, time) in tests/e2e/test_hybrid_workflows.py
- [X] T093 [P] [US4] Test concurrent mark_community_as_read_with_history calls for different communities complete without race conditions in tests/e2e/test_hybrid_workflows.py
- [X] T094 [P] [US4] Test mark_community_as_read_with_history clears Baileys temp DB after completion in tests/e2e/test_hybrid_workflows.py
- [X] T095 [P] [US4] Test mark_community_as_read_with_history updates checkpoints correctly in tests/e2e/test_hybrid_workflows.py

**Checkpoint**: At this point, hybrid workflows should work reliably end-to-end

---

## Phase 7: User Story 5 - Backend Failover Resilience (Priority: P5)

**Goal**: Verify system handles backend failures gracefully with automatic failover

**Independent Test**: Run `pytest tests/integration/test_failover.py -v` and verify all failover scenarios succeed

### Integration Tests for User Story 5

- [X] T096 [US5] Create tests/integration/test_failover.py file
- [X] T097 [P] [US5] Test automatic failover when Go backend becomes unreachable mid-operation in tests/integration/test_failover.py
- [X] T098 [P] [US5] Test automatic failover when Baileys backend becomes unreachable mid-operation in tests/integration/test_failover.py
- [X] T099 [P] [US5] Test system returns "No backend available" error when both backends fail simultaneously in tests/integration/test_failover.py
- [X] T100 [P] [US5] Test backend recovery detection after Go backend restarts in tests/integration/test_failover.py
- [X] T101 [P] [US5] Test backend recovery detection after Baileys backend restarts in tests/integration/test_failover.py
- [X] T102 [P] [US5] Test operations fail fast (under 10s) when no backends available in tests/integration/test_failover.py
- [X] T103 [P] [US5] Test FASTEST strategy switches to faster backend when response times change in tests/integration/test_failover.py
- [X] T104 [P] [US5] Test failover handles network partition (backend unreachable but not crashed) in tests/integration/test_failover.py

**Checkpoint**: At this point, failover resilience should be validated with real backends

---

## Phase 8: User Story 6 - Concurrent Operation Safety (Priority: P6)

**Goal**: Verify system handles concurrent operations without race conditions, deadlocks, or resource exhaustion

**Independent Test**: Run `pytest tests/integration/test_concurrent_operations.py -v` and verify all concurrency tests pass

### Integration Tests for User Story 6

- [X] T105 [US6] Create tests/integration/test_concurrent_operations.py file
- [X] T106 [P] [US6] Test 10 concurrent message send operations complete without errors in tests/integration/test_concurrent_operations.py
- [X] T107 [P] [US6] Test 5 concurrent database sync operations for different chats complete without deadlocks in tests/integration/test_concurrent_operations.py
- [X] T108 [P] [US6] Test 20 concurrent health checks complete in under 10 seconds in tests/integration/test_concurrent_operations.py
- [X] T109 [P] [US6] Test concurrent route_with_fallback calls handle failover correctly without race conditions in tests/integration/test_concurrent_operations.py
- [X] T110 [P] [US6] Test 100 mixed concurrent operations (send, sync, health) complete successfully in tests/integration/test_concurrent_operations.py
- [X] T111 [P] [US6] Test concurrent sync operations for same chat handle overlapping correctly (no duplicates) in tests/integration/test_concurrent_operations.py
- [X] T112 [P] [US6] Test concurrent operations with thread barrier synchronization (all start simultaneously) in tests/integration/test_concurrent_operations.py
- [X] T113 [P] [US6] Test race condition detector identifies no conflicts in concurrent operations in tests/integration/test_concurrent_operations.py

**Checkpoint**: At this point, concurrency safety should be validated under load

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Coverage reporting, documentation, and CI/CD integration

- [X] T114 [P] Create .github/workflows/tests.yml for GitHub Actions CI/CD
- [X] T115 [P] Configure Codecov integration in .github/workflows/tests.yml
- [X] T116 [P] Add coverage badge to README.md (if exists)
- [X] T117 [P] Verify all edge cases from spec.md have corresponding test coverage
- [X] T118 Run full test suite and verify overall coverage ≥70%
- [X] T119 Run pytest --cov=routing --cov-report=term-missing and verify routing.py ≥80%
- [X] T120 Run pytest --cov=sync --cov-report=term-missing and verify sync.py ≥75%
- [X] T121 Run pytest --cov=backends/health --cov-report=term-missing and verify health.py ≥75%
- [X] T122 Generate HTML coverage report and review uncovered lines
- [X] T123 [P] Update quickstart.md with actual test execution examples (if needed)
- [X] T124 [P] Add test-running instructions to main README.md
- [X] T125 Verify all tests pass in CI/CD pipeline
- [X] T126 Verify coverage threshold enforcement (fail below 70%)
- [X] T127 Run full integration test suite with Docker Compose
- [X] T128 Validate test suite detects intentional regression (effectiveness check)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T011) - BLOCKS all test writing
- **User Story 1 (Phase 3)**: Depends on Foundational (T012-T026) - No dependencies on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational (T012-T026) - Can run in parallel with US1
- **User Story 3 (Phase 5)**: Depends on Foundational (T012-T026) - Can run in parallel with US1/US2
- **User Story 4 (Phase 6)**: Depends on Foundational (T012-T026) - Can run in parallel with US1-US3
- **User Story 5 (Phase 7)**: Depends on Foundational (T012-T026) - Can run in parallel with other stories
- **User Story 6 (Phase 8)**: Depends on Foundational (T012-T026) - Can run in parallel with other stories
- **Polish (Phase 9)**: Depends on ALL user stories completion - validates full coverage

### User Story Dependencies

- **User Story 1 (P1 - Routing)**: Can start after Foundational - Fully independent
- **User Story 2 (P2 - Sync)**: Can start after Foundational - Fully independent
- **User Story 3 (P3 - Health)**: Can start after Foundational - Fully independent
- **User Story 4 (P4 - Hybrid Workflows)**: Can start after Foundational - Tests integration but independently verifiable
- **User Story 5 (P5 - Failover)**: Can start after Foundational - Tests system behavior but independently verifiable
- **User Story 6 (P6 - Concurrency)**: Can start after Foundational - Tests load behavior but independently verifiable

### Within Each User Story

- All tests marked [P] within a story can run in parallel (different test functions)
- Tests can be written in any order within a story
- Story complete when all tests pass and coverage target met

### Parallel Opportunities

- All Setup tasks (T001-T011) marked [P] can run in parallel
- All Foundational fixture tasks marked [P] can run in parallel within their groups
- Once Foundational completes, ALL 6 user stories can be worked on in parallel
- All tests within each user story marked [P] can run in parallel
- Different developers can work on different user stories simultaneously

---

## Parallel Example: User Story 1 (Routing Tests)

```bash
# All routing tests can be written in parallel (different test functions):
Task T027: "Test routing selects Go backend when Baileys is down"
Task T028: "Test routing selects Baileys backend when Go is down"
Task T029: "Test routing prefers Baileys for SYNC_FULL_HISTORY"
Task T030: "Test routing prefers Go for SEND_MESSAGE"
# ... all 21 routing tests can run simultaneously

# Verify coverage after all tests written:
pytest tests/unit/test_routing.py --cov=routing --cov-report=term-missing
```

---

## Parallel Example: All User Stories After Foundation

```bash
# Once Foundational (Phase 2) completes, all stories can proceed in parallel:

Developer A: Phase 3 (US1 - Routing tests T027-T047)
Developer B: Phase 4 (US2 - Sync tests T048-T066)
Developer C: Phase 5 (US3 - Health tests T067-T087)
Developer D: Phase 6 (US4 - Hybrid workflow tests T088-T095)
Developer E: Phase 7 (US5 - Failover tests T096-T104)
Developer F: Phase 8 (US6 - Concurrency tests T105-T113)

# Each developer can complete their story independently
# Then Polish phase (Phase 9) validates everything together
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - Routing Coverage)

1. Complete Phase 1: Setup (T001-T011) → ~30 minutes
2. Complete Phase 2: Foundational (T012-T026) → ~2 hours
3. Complete Phase 3: User Story 1 (T027-T047) → ~4 hours
4. **STOP and VALIDATE**:
   - Run `pytest tests/unit/test_routing.py --cov=routing --cov-report=html`
   - Verify routing.py ≥80% coverage
   - Open htmlcov/index.html and review uncovered lines
5. **MVP COMPLETE** - Critical routing path now fully tested

**MVP Rationale**: Routing is the critical path for ALL requests (0% → 80% coverage). Validating this first provides immediate confidence for routing changes.

### Incremental Delivery (Priority Order)

1. Setup + Foundational → Test infrastructure ready (~2.5 hours)
2. User Story 1 (Routing) → Validate independently → **MVP Milestone** (~4 hours, total: 6.5h)
3. User Story 2 (Sync) → Validate independently → Database sync confidence (~3 hours, total: 9.5h)
4. User Story 3 (Health) → Validate independently → Health monitoring confidence (~3 hours, total: 12.5h)
5. User Story 4 (Hybrid) → Validate independently → E2E workflow confidence (~2 hours, total: 14.5h)
6. User Story 5 (Failover) → Validate independently → Resilience confidence (~2 hours, total: 16.5h)
7. User Story 6 (Concurrency) → Validate independently → Load handling confidence (~2 hours, total: 18.5h)
8. Polish → Coverage reporting + CI/CD → **Full Delivery** (~1.5 hours, total: 20h)

**Each story adds value without breaking previous stories**

### Parallel Team Strategy (6 developers)

With 6 developers available:

1. **Together**: Complete Setup + Foundational (~2.5 hours)
2. **Once Foundational completes, split work**:
   - Developer A: User Story 1 (Routing) - 4 hours
   - Developer B: User Story 2 (Sync) - 3 hours
   - Developer C: User Story 3 (Health) - 3 hours
   - Developer D: User Story 4 (Hybrid) - 2 hours
   - Developer E: User Story 5 (Failover) - 2 hours
   - Developer F: User Story 6 (Concurrency) - 2 hours
3. **Parallel completion**: Max 4 hours (longest story)
4. **Together**: Polish phase (~1.5 hours)

**Total time with 6 developers: ~8 hours (vs. 20 hours sequential)**

---

## Coverage Targets Summary

| Module | Lines | Current | Target | Tests |
|--------|-------|---------|--------|-------|
| **routing.py** | 341 | 0% | 80% | T027-T047 (21 tests) |
| **sync.py** | 410 | minimal | 75% | T048-T066 (19 tests) |
| **backends/health.py** | 391 | minimal | 75% | T067-T087 (21 tests) |
| **Overall** | ~1200 | 20% | 70-80% | 128 total tasks |

---

## Notes

- [P] tasks = different test functions or files, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable (coverage target + all tests pass)
- Tests use mock backends (unit) or real backends (integration) per design
- Commit after each test file or logical group (every 5-10 tests)
- Stop at any checkpoint to validate story coverage independently
- Integration tests (US4-US6) require both bridges running via Docker Compose
- Concurrent tests (US6) use ThreadPoolExecutor + Barrier for synchronization
- Coverage measurement automatic via pytest-cov (configured in Phase 1)
