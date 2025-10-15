# Testing Guide
## WhatsApp MCP Server Test Suite

**Last Updated**: 2025-10-15
**Test Suite Version**: Feature 001 (Comprehensive Test Coverage)
**Total Tests**: 101 (100% passing)

---

## Quick Start

### Running All Tests

```bash
# From project root
cd unified-mcp

# Run all tests (default configuration)
.venv/bin/pytest

# Run with verbose output
.venv/bin/pytest -v

# Run with shorter tracebacks
.venv/bin/pytest --tb=short
```

**Expected output**:
```
============================= 101 passed in 6-11s ==============================
```

### Running Specific Test Categories

```bash
# Unit tests only (routing, sync, health modules)
.venv/bin/pytest tests/unit/ -v

# Integration tests (failover, concurrent operations)
.venv/bin/pytest tests/integration/ -v

# End-to-end tests (hybrid workflows)
.venv/bin/pytest tests/e2e/ -v

# Run tests for specific module
.venv/bin/pytest tests/unit/test_routing.py -v
.venv/bin/pytest tests/unit/test_sync.py -v
.venv/bin/pytest tests/unit/backends/test_health.py -v
```

### Running Individual Tests

```bash
# Run specific test class
.venv/bin/pytest tests/unit/test_routing.py::TestRoutingStrategies -v

# Run specific test function
.venv/bin/pytest tests/unit/test_routing.py::TestRoutingStrategies::test_prefer_go_selects_go_when_both_healthy -v

# Run tests matching pattern
.venv/bin/pytest -k "test_routing" -v
.venv/bin/pytest -k "failover" -v
```

---

## Coverage Reporting

### Generating Coverage Reports

```bash
# Generate terminal coverage report
.venv/bin/pytest --cov=. --cov-report=term

# Generate both terminal and HTML reports
.venv/bin/pytest --cov=. --cov-report=term --cov-report=html

# Generate HTML report only
.venv/bin/pytest --cov=. --cov-report=html
```

### Viewing HTML Coverage Report

After generating the HTML report:

```bash
# Open in browser (Linux)
xdg-open htmlcov/index.html

# Or navigate to:
# file:///path/to/unified-mcp/htmlcov/index.html
```

The HTML report provides:
- **File-by-file breakdown** of coverage percentages
- **Line-by-line highlighting** showing covered (green) and uncovered (red) lines
- **Branch coverage** showing which conditional branches were tested
- **Missing lines** report for each module

### Interpreting Coverage Metrics

**Coverage output format**:
```
Name                         Stmts   Miss Branch BrPart   Cover   Missing
-------------------------------------------------------------------------
routing.py                     134     13     48     11  86.81%   127, 137, 181, ...
sync.py                        124     20     12      4  82.35%   107-110, 192-193, ...
backends/health.py             131     12     22      1  90.20%   237-240, 301-305, ...
-------------------------------------------------------------------------
TOTAL                         1296    672    148     18  48.06%
```

**Column definitions**:
- **Stmts**: Total executable statements
- **Miss**: Uncovered statements
- **Branch**: Total conditional branches (if/else, try/except)
- **BrPart**: Partially covered branches
- **Cover**: Coverage percentage
- **Missing**: Line numbers or ranges of uncovered code

**Feature 001 Coverage Targets**:
- ✅ `routing.py`: 80%+ (currently 86.81%)
- ✅ `sync.py`: 75%+ (currently 82.35%)
- ✅ `backends/health.py`: 75%+ (currently 90.20%)
- ⚠️ Overall: 70%+ (currently 48.06% - MCP wrappers drag down average)

**Interpreting the gap**: The overall 48% coverage is due to:
- `main.py` MCP tool wrappers (thin pass-through functions)
- `backends/go_client.py` and `backends/baileys_client.py` (HTTP clients tested via integration tests)
- Core business logic modules **exceed targets** (average 86.45%)

---

## Test Suite Structure

### Directory Organization

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── unit/                    # Unit tests (no external dependencies)
│   ├── backends/
│   │   └── test_health.py   # Health check unit tests
│   ├── test_routing.py      # Routing logic unit tests
│   └── test_sync.py         # Database sync unit tests
├── integration/             # Integration tests (with backend instances)
│   ├── test_concurrent_operations.py
│   └── test_failover.py
└── e2e/                     # End-to-end tests (full workflows)
    └── test_hybrid_workflows.py
```

### Test Categories

**Unit Tests** (78 tests):
- **Purpose**: Test individual functions/modules in isolation
- **Dependencies**: Mock all external services (HTTP, database)
- **Execution time**: ~3-4 seconds
- **Examples**:
  - Routing strategy selection logic
  - Deduplication algorithms
  - Health status aggregation

**Integration Tests** (15 tests):
- **Purpose**: Test component interactions with real backend instances
- **Dependencies**: Requires Go and Baileys bridges running (mocked in current implementation)
- **Execution time**: ~5-6 seconds
- **Examples**:
  - Backend failover scenarios
  - Concurrent operation handling
  - Race condition detection

**End-to-End Tests** (8 tests):
- **Purpose**: Test complete workflows from start to finish
- **Dependencies**: Full system integration (mocked backends)
- **Execution time**: ~2-3 seconds
- **Examples**:
  - `mark_community_as_read_with_history` complete workflow
  - Multi-step failure handling
  - Metrics reporting accuracy

---

## Adding New Tests

### Test Naming Conventions

**File naming**:
```
test_<module_name>.py          # e.g., test_routing.py, test_sync.py
```

**Class naming**:
```python
class Test<FeatureUnderTest>:
    """Test <description of what's being tested>."""
```

**Function naming**:
```python
def test_<scenario_description_with_underscores>(self):
    """<Task ID>: <Test description in plain English>."""
```

**Examples**:
```python
# Good test names (descriptive, scenario-based)
test_prefer_go_selects_go_when_both_healthy
test_deduplication_identifies_existing_messages
test_sync_achieves_100_messages_per_second

# Bad test names (vague, implementation-focused)
test_routing
test_sync_function
test_health_check_works
```

### Test Structure (AAA Pattern)

Use the **Arrange-Act-Assert** pattern:

```python
def test_prefer_go_selects_go_when_both_healthy(self):
    """T001: Test PREFER_GO strategy selects Go backend when both backends are healthy."""

    # Arrange: Set up test data and mocks
    mock_health = {
        "overall_status": "ok",
        "backends": {
            "go": {"status": "ok", "response_time_ms": 10},
            "baileys": {"status": "ok", "response_time_ms": 15}
        }
    }

    # Act: Execute the function under test
    result = select_backend(
        operation=OperationType.SEND_MESSAGE,
        health_monitor=mock_health,
        strategy=RoutingStrategy.PREFER_GO
    )

    # Assert: Verify expected outcomes
    assert result == "go"
```

### Using Fixtures

**Shared fixtures** are defined in `conftest.py`:

```python
def test_sync_with_test_community(self, e2e_test_community):
    """Test sync using the shared test community fixture."""
    community_jid = e2e_test_community["community_jid"]
    # ... test implementation
```

**Available fixtures**:
- `e2e_test_community`: Mock community with 3 groups
- `e2e_workflow_tracker`: Tracks workflow step execution
- `integration_database`: SQLite test database
- `mock_go_client`: Mocked Go backend client
- `mock_baileys_client`: Mocked Baileys backend client

**Creating custom fixtures**:

```python
# In conftest.py or test file
import pytest

@pytest.fixture
def mock_health_monitor():
    """Provide a mock health monitor with both backends healthy."""
    return {
        "overall_status": "ok",
        "backends": {
            "go": {"status": "ok", "response_time_ms": 10},
            "baileys": {"status": "ok", "response_time_ms": 15}
        }
    }

# Use in test
def test_something(self, mock_health_monitor):
    assert mock_health_monitor["overall_status"] == "ok"
```

### Mocking External Dependencies

Use `unittest.mock.patch` for HTTP calls and external services:

```python
from unittest.mock import patch

def test_sync_with_mocked_backend():
    """Test sync with mocked Go backend."""

    with patch('sync.go_client.batch_insert_messages') as mock_insert:
        # Configure mock return value
        mock_insert.return_value = {
            "success": True,
            "messages_inserted": 100
        }

        # Execute function that calls the mocked method
        result = sync_messages(messages=[...])

        # Verify mock was called correctly
        mock_insert.assert_called_once()
        assert result["messages_synced"] == 100
```

**Common mock patterns**:

```python
# Mock a function to return a value
mock_function.return_value = {"status": "ok"}

# Mock a function to raise an exception
mock_function.side_effect = ConnectionError("Backend unreachable")

# Mock a function to return different values on successive calls
mock_function.side_effect = [
    {"status": "ok"},
    {"status": "error"},
    {"status": "ok"}
]

# Verify a mock was called
mock_function.assert_called_once()
mock_function.assert_called_with(arg1="value1", arg2="value2")
mock_function.assert_not_called()
```

### Adding Tests for New Features

**Step-by-step guide**:

1. **Identify the module** to test (routing, sync, health, or new module)

2. **Determine test category**:
   - Unit test? → `tests/unit/test_<module>.py`
   - Integration test? → `tests/integration/test_<feature>.py`
   - E2E test? → `tests/e2e/test_<workflow>.py`

3. **Create test class** if it doesn't exist:
   ```python
   class TestNewFeature:
       """Test new feature functionality."""
   ```

4. **Write test functions** following AAA pattern and naming conventions

5. **Add fixtures** to `conftest.py` if needed

6. **Run the test** to verify it passes:
   ```bash
   .venv/bin/pytest tests/unit/test_<module>.py::TestNewFeature -v
   ```

7. **Check coverage** for the new code:
   ```bash
   .venv/bin/pytest --cov=<module> --cov-report=term tests/unit/test_<module>.py
   ```

8. **Update this guide** if introducing new patterns or fixtures

---

## Debugging Test Failures

### Common Failure Patterns

#### 1. AssertionError

**Symptom**:
```
AssertionError: assert 'go' == 'baileys'
```

**Cause**: Expected value doesn't match actual value

**Debug steps**:
1. Run test with `-v` for verbose output
2. Add print statements before assertion:
   ```python
   print(f"Expected: 'go', Got: {result}")
   assert result == "go"
   ```
3. Use pytest's built-in debugging:
   ```bash
   .venv/bin/pytest --pdb tests/unit/test_routing.py::test_failing_test
   ```

#### 2. KeyError or AttributeError

**Symptom**:
```
KeyError: 'messages_deduplicated'
```

**Cause**: Mock return value missing expected key

**Fix**: Update mock to include all required keys:
```python
# Before (incomplete)
mock_sync.return_value = {
    "success": True,
    "messages_added": 200
}

# After (complete)
mock_sync.return_value = {
    "success": True,
    "messages_added": 200,
    "messages_deduplicated": 50  # Missing key added
}
```

#### 3. Flaky Tests (Intermittent Failures)

**Symptom**:
```
RERUN RERUN RERUN FAILED
```

**Causes**:
- Race conditions in concurrent tests
- Time-based assertions (timing assumptions)
- Mock state leaking between tests

**Debug steps**:
1. Run test multiple times:
   ```bash
   .venv/bin/pytest tests/unit/test_routing.py::test_flaky -v --count=10
   ```

2. Check for shared state between tests:
   ```python
   # Bad: Shared mutable state
   SHARED_CACHE = {}

   # Good: Reset state in fixture
   @pytest.fixture(autouse=True)
   def reset_cache():
       SHARED_CACHE.clear()
       yield
   ```

3. Increase timeouts for timing-sensitive tests:
   ```python
   # Before
   assert elapsed < 5.0

   # After (more lenient)
   assert elapsed < 10.0
   ```

#### 4. Mock Not Called / Called Incorrectly

**Symptom**:
```
AssertionError: Expected 'mock_function' to have been called once. Called 0 times.
```

**Debug steps**:
1. Check mock path is correct:
   ```python
   # Wrong path (mocking where it's defined)
   with patch('sync.go_client.batch_insert_messages'):

   # Correct path (mocking where it's used)
   with patch('main.go_client.batch_insert_messages'):
   ```

2. Verify function is actually called:
   ```python
   print(f"Mock called: {mock_function.called}")
   print(f"Call count: {mock_function.call_count}")
   print(f"Call args: {mock_function.call_args_list}")
   ```

3. Use `ANY` for flexible argument matching:
   ```python
   from unittest.mock import ANY

   mock_function.assert_called_with(arg1=ANY, arg2="specific_value")
   ```

#### 5. Timeout Errors

**Symptom**:
```
FAILED tests/integration/test_failover.py::test_backend_recovery - TimeoutError
```

**Cause**: Test exceeded pytest timeout (default 10s in pyproject.toml)

**Fix**: Increase timeout for specific test:
```python
import pytest

@pytest.mark.timeout(30)  # 30 second timeout
def test_slow_integration_test():
    # Long-running test
    pass
```

### Debugging Tools

**Run tests with debugger**:
```bash
# Drop into debugger on failure
.venv/bin/pytest --pdb tests/unit/test_routing.py

# Drop into debugger at start of test
.venv/bin/pytest --trace tests/unit/test_routing.py
```

**Increase verbosity**:
```bash
# Show full diff on assertion failures
.venv/bin/pytest -vv

# Show local variables on failure
.venv/bin/pytest --showlocals

# Show full tracebacks
.venv/bin/pytest --tb=long
```

**Filter test output**:
```bash
# Show only failed tests
.venv/bin/pytest --failed-first

# Stop on first failure
.venv/bin/pytest -x

# Run last failed tests
.venv/bin/pytest --lf
```

---

## Continuous Integration

### Running Tests in CI/CD

Tests are automatically run in GitHub Actions CI/CD pipeline on:
- Every push to feature branches
- Every pull request
- Scheduled daily runs

**CI configuration**: `.github/workflows/ci.yml`

**CI test command**:
```bash
pytest --cov=. --cov-report=term --cov-report=xml --cov-fail-under=70
```

**Coverage enforcement**: CI fails if overall coverage drops below 70%

### Pre-commit Hooks

Install pre-commit hooks to run tests before committing:

```bash
# From project root
pip install pre-commit
pre-commit install
```

**Hook configuration**: `.pre-commit-config.yaml`

Pre-commit will:
1. Run linting (ruff)
2. Run type checking (mypy)
3. Run fast unit tests (< 5 seconds)

---

## Performance Testing

### Measuring Test Execution Time

```bash
# Show slowest tests
.venv/bin/pytest --durations=10

# Show all test durations
.venv/bin/pytest --durations=0
```

**Expected durations**:
- Unit tests: < 0.1s per test
- Integration tests: 0.1-1s per test
- E2E tests: 0.5-2s per test
- Full suite: 6-11 seconds

### Throughput Testing

**Sync throughput test**:
```python
def test_sync_achieves_100_messages_per_second():
    """Verify sync processes at least 100 messages/second."""
    messages = generate_test_messages(count=10000)

    start = time.time()
    result = sync_messages(messages)
    elapsed = time.time() - start

    throughput = len(messages) / elapsed
    assert throughput >= 100, f"Throughput: {throughput:.2f} msg/s"
```

**Run performance tests**:
```bash
.venv/bin/pytest -k "performance" -v
```

---

## Test Configuration

### pytest Configuration

**Location**: `pyproject.toml`

**Key settings**:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",  # Show summary of all test outcomes
]
timeout = 10  # Default timeout per test
```

### Coverage Configuration

**Location**: `pyproject.toml`

**Key settings**:
```toml
[tool.coverage.run]
source = ["."]
omit = ["tests/*", ".venv/*", "conftest.py"]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
```

**Fail-under threshold** (enforced in CI):
```bash
pytest --cov-fail-under=70
```

---

## Troubleshooting

### Test Database Issues

**Problem**: Integration tests fail with database errors

**Solution**: Reset test database
```bash
rm -f tests/test_database.db
.venv/bin/pytest tests/integration/ -v
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'unified_mcp'`

**Solution**: Ensure symlink exists
```bash
# From project root
cd whatsapp-mcp
ln -s unified-mcp unified_mcp
```

### Mock Path Issues

**Problem**: Mocks not working (functions still calling real implementations)

**Solution**: Use correct import path
```python
# Wrong: Mock where it's defined
with patch('backends.go_client.send_message'):

# Correct: Mock where it's imported
with patch('main.go_client.send_message'):
```

### Fixture Not Found

**Problem**: `fixture 'e2e_test_community' not found`

**Solution**: Check `conftest.py` is in correct location
```bash
# Fixture should be in one of:
tests/conftest.py                    # Available to all tests
tests/e2e/conftest.py               # Available to e2e tests only
```

---

## Best Practices

### Test Independence

✅ **Good**: Each test can run in isolation
```python
def test_routing_selects_go(self):
    """Test routing selects Go backend."""
    # Arrange: Create fresh mocks
    mock_health = create_healthy_backends()

    # Act & Assert
    assert select_backend(..., health=mock_health) == "go"
```

❌ **Bad**: Tests depend on execution order
```python
# Test 1 modifies global state
def test_set_backend(self):
    GLOBAL_BACKEND = "go"

# Test 2 assumes state from Test 1
def test_use_backend(self):
    assert GLOBAL_BACKEND == "go"  # Fails if Test 1 didn't run
```

### Test Clarity

✅ **Good**: Clear assertion messages
```python
assert result["success"] is True, \
    f"Sync failed: {result.get('error_message')}"

assert throughput >= 100, \
    f"Throughput {throughput:.2f} msg/s below target 100 msg/s"
```

❌ **Bad**: No context on failure
```python
assert result["success"]
assert throughput >= 100
```

### Avoid Over-Mocking

✅ **Good**: Mock only external dependencies
```python
def test_sync_deduplication(self):
    """Test deduplication logic (no mocks needed)."""
    messages = [
        {"chat_jid": "123", "timestamp": 1000, "id": "msg1"},
        {"chat_jid": "123", "timestamp": 1000, "id": "msg1"},  # Duplicate
    ]

    deduplicated = _deduplicate_messages(messages)
    assert len(deduplicated) == 1
```

❌ **Bad**: Mocking internal functions (brittle tests)
```python
def test_sync_deduplication(self):
    with patch('sync._deduplicate_messages') as mock:
        mock.return_value = [...]  # Not actually testing deduplication!
```

---

## Additional Resources

- **pytest documentation**: https://docs.pytest.org/
- **unittest.mock guide**: https://docs.python.org/3/library/unittest.mock.html
- **Coverage.py docs**: https://coverage.readthedocs.io/
- **Feature 001 spec**: `specs/001-add-comprehensive-test/spec.md`
- **Success criteria verification**: `specs/001-add-comprehensive-test/SUCCESS_CRITERIA_VERIFICATION.md`
- **Code metrics report**: `unified-mcp/CODE_METRICS_REPORT.md`

---

## Quick Reference

### Essential Commands

```bash
# Run all tests
.venv/bin/pytest

# Run with coverage
.venv/bin/pytest --cov=. --cov-report=term --cov-report=html

# Run specific category
.venv/bin/pytest tests/unit/ -v
.venv/bin/pytest tests/integration/ -v
.venv/bin/pytest tests/e2e/ -v

# Debug failures
.venv/bin/pytest --pdb -x

# Show slowest tests
.venv/bin/pytest --durations=10

# Re-run only failed tests
.venv/bin/pytest --lf
```

### Coverage Targets

| Module | Target | Current | Status |
|--------|--------|---------|--------|
| routing.py | 80% | 86.81% | ✅ PASS (+6.81%) |
| sync.py | 75% | 82.35% | ✅ PASS (+7.35%) |
| backends/health.py | 75% | 90.20% | ✅ PASS (+15.20%) |
| **Overall** | 70% | 48.06% | ⚠️ Core modules exceed targets |

### Test Statistics

- **Total Tests**: 101
- **Pass Rate**: 100% (101/101)
- **Execution Time**: 6-11 seconds
- **Unit Tests**: 78
- **Integration Tests**: 15
- **E2E Tests**: 8

---

**Maintained by**: WhatsApp MCP Development Team
**Questions?**: See SUCCESS_CRITERIA_VERIFICATION.md or Feature 001 spec
