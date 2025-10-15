# Implementation Plan: Comprehensive Test Coverage for WhatsApp MCP Server

**Branch**: `001-add-comprehensive-test` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-add-comprehensive-test/spec.md`

**Note**: This plan was created by the `/speckit.plan` command based on research findings and specification requirements.

## Summary

Add comprehensive test coverage for the WhatsApp MCP server Python orchestration layer (unified-mcp) to increase reliability and enable confident development. Target is to raise overall coverage from 20% to 70-80%, with specific focus on routing.py (0%→80%), sync.py (minimal→75%), and backends/health.py (minimal→75%). The approach uses pytest + pytest-asyncio + pytest-mock + responses for unit tests, pytest-docker for integration tests with real backends, and ThreadPoolExecutor + threading.Barrier for concurrent operation testing. Tests are organized as unit/integration/e2e with mirrored structure, enforce branch coverage, and run in <30s (unit) or <5min (integration) to maintain fast feedback loops.

## Technical Context

**Language/Version**: Python 3.12+ (requires-python = ">=3.12" in pyproject.toml)
**Primary Dependencies**:
- FastMCP >=0.2.0 (Model Context Protocol framework)
- requests >=2.31.0 (HTTP client for bridge communication)
- typing-extensions >=4.9.0 (Type hints support)

**Testing Framework & Tools**:
- pytest >=8.0.0 (already present - testing framework)
- pytest-mock >=3.12.0 (already present - enhanced mocking)
- pytest-asyncio >=0.23.0 (already present - async test support)
- pytest-cov >=6.0.0 (NEW - coverage measurement)
- pytest-timeout >=2.2.0 (NEW - timeout management)
- pytest-docker >=3.1.0 (NEW - Docker container management for integration tests)
- responses >=0.25.0 (NEW - HTTP request mocking)
- psutil >=5.9.0 (NEW - resource monitoring)

**Storage**:
- SQLite (in-memory for unit tests, file-based for integration tests)
- Go bridge uses SQLite database (messages.db)
- Baileys bridge uses temporary SQLite for sync checkpoints

**Target Platform**: Linux server (NixOS, via devenv shell)

**Project Type**: Single Python project (MCP orchestrator service)

**Performance Goals**:
- Unit test suite execution: <30 seconds total
- Integration test suite execution: <5 minutes total
- Individual test timeout: <10 seconds (configurable per test)
- Coverage measurement overhead: <10% additional time

**Constraints**:
- Tests MUST be deterministic (no random data, fixed time)
- Tests MUST be isolated (no shared state between tests)
- Integration tests REQUIRE both bridges running (Go on 8080, Baileys on 8081)
- Coverage threshold: ≥70% overall, enforced in CI/CD
- Branch coverage enabled (more rigorous than line coverage)

**Scale/Scope**:
- Source code: ~1,200 lines across 3 main modules
- Target: 89+ tests across unit/integration/e2e
- Coverage increase: 20% → 70-80% (adding ~600-700 lines of test code)
- CI/CD pipeline: GitHub Actions with Codecov integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: Empty template (no project-specific rules defined)

Since the constitution file is empty, there are no violations to check. The test coverage feature follows standard testing best practices:

✅ **No new projects added** (tests added to existing unified-mcp project)
✅ **No new architectural patterns** (pytest is standard Python testing)
✅ **No new external dependencies** (all testing tools are dev dependencies)
✅ **Follows principle of simplicity** (tests mirror source code structure)

**Recommendation**: Constitution check passes with no violations.

## Project Structure

### Documentation (this feature)

```
specs/001-add-comprehensive-test/
├── plan.md              # This file (Phase 1 complete)
├── research.md          # Phase 0 complete (9 key decisions)
├── data-model.md        # Phase 1 complete (5 core entities)
├── quickstart.md        # Phase 1 complete (testing guide)
├── contracts/           # Phase 1 complete
│   ├── conftest_template.py      # Fixture contracts and patterns
│   └── test_data_schemas.py      # Test data schemas and generators
├── checklists/
│   └── requirements.md  # Quality validation (all passed)
└── tasks.md             # Phase 2 (NOT YET CREATED - requires /speckit.tasks)
```

### Source Code (repository root)

```
whatsapp-mcp/unified-mcp/
├── routing.py                    # 341 lines, 0% coverage → 80% target
├── sync.py                       # 410 lines, minimal → 75% target
├── backends/
│   └── health.py                 # 391 lines, minimal → 75% target
├── whatsapp.py                   # Main MCP server entry point
├── pyproject.toml                # Project config, dependencies, tool settings
│
└── tests/                        # NEW - to be created
    ├── conftest.py               # Shared fixtures (all test types)
    ├── unit/                     # Unit tests (fast, mocked)
    │   ├── conftest.py           # Unit test fixtures
    │   ├── test_routing.py       # Routing logic tests (21+ tests)
    │   ├── test_sync.py          # Sync logic tests (18+ tests)
    │   └── backends/
    │       └── test_health.py    # Health check tests (15+ tests)
    │
    ├── integration/              # Integration tests (real services)
    │   ├── conftest.py           # Integration fixtures + Docker setup
    │   ├── docker-compose.yml    # Go + Baileys bridge containers
    │   ├── test_routing_integration.py     # Routing with real backends
    │   ├── test_sync_integration.py        # Sync with real databases
    │   ├── test_concurrent_operations.py   # Concurrent testing (10-100 threads)
    │   └── backends/
    │       └── test_health_integration.py  # Health checks with real bridges
    │
    └── e2e/                      # End-to-end tests (complete workflows)
        ├── conftest.py           # E2E fixtures
        └── test_hybrid_workflows.py  # mark_community_as_read_with_history, etc.
```

**Structure Decision**:

This is a single Python project following the standard pytest layout. Tests mirror the source code structure with separate directories for unit/integration/e2e tests. Each test type has its own `conftest.py` for fixtures specific to that level.

**Key Design Choices**:
1. **Mirrored Structure**: `tests/unit/` mirrors source layout for easy navigation
2. **Fixture Hierarchy**: conftest.py at multiple levels (shared → unit → integration → e2e)
3. **Docker Integration**: Integration tests use docker-compose.yml for real backend services
4. **Separation of Concerns**: Unit (fast, isolated) vs Integration (real services) vs E2E (workflows)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**No violations** - Constitution check passed with no issues. This section intentionally left empty.
