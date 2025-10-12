# Changelog

All notable changes to the WhatsApp MCP Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-10-12

### Added - Feature 002: CI/CD Pipeline with Quality Gates
- GitHub Actions workflows for automated testing and quality checks (specs/002-add-ci-cd)
- Automated test execution on all PRs (Python 3.12 + 3.13 matrix)
- Automatic retry for flaky tests (pytest-rerunfailures, 3 retries with 1s delay)
- Code quality checks: ruff formatting, ruff linting, mypy type checking
- Multi-language build verification (Go, TypeScript, Python)
- Security scanning: Semgrep (SAST), Trivy (dependencies), Gitleaks (secrets)
- Test coverage reporting via Codecov (70% minimum threshold)
- Fail-open strategy for external service resilience
- 9 required status checks before merge

### Added - Feature 001: Comprehensive Test Coverage
- 101 tests covering routing, sync, health, failover, concurrent operations (specs/001-add-comprehensive-test)
- Unit tests: 52 tests with 80%+ coverage on core modules
  - routing.py: 83.80% coverage
  - sync.py: 82.48% coverage
  - backends/health.py: 87.66% coverage
- Integration tests: 24 tests for hybrid workflows and backend failover
- E2E tests: 25 tests for mark_community_as_read_with_history and concurrent operations
- Thread barrier synchronization for concurrent operation testing
- Race condition detection framework
- Automatic retry logic with flaky test detection

### Fixed
- Fixed mark_chat_read_v2 endpoint URL (was /api/mark_as_read, now /api/mark_read)
- Go bridge now accepts empty message_ids array to mark all messages in chat
- Added database index idx_messages_chat_timestamp for O(log n) query performance

### Added - Core Features
- Structured error codes: EMPTY_CHAT, CHAT_NOT_FOUND, INVALID_JID, DATABASE_ERROR, WHATSAPP_API_ERROR
- Automatic batching for 10,000+ messages (1000 per batch)
- mark_message_read() convenience wrapper for single messages

### Performance
- Marking all messages in chat now requires 1 API call (was 2: query + mark)
- Database query time: <1ms with index (was 50-100ms without)
- 10,000 messages marked in <5 seconds
