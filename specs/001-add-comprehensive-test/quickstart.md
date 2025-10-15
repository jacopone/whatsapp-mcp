# Quick Start: Running Tests for WhatsApp MCP Server

**Branch**: `001-add-comprehensive-test` | **Date**: 2025-10-12

**Purpose**: Step-by-step guide for running, interpreting, and adding tests to the WhatsApp MCP server test suite.

---

## Prerequisites

Before running tests, ensure you have:

1. **Python 3.12+** installed
2. **Go bridge** and **Baileys bridge** available (for integration tests)
3. **Docker** and **Docker Compose** (for integration tests with containers)
4. **Test dependencies** installed (see Installation below)

---

## Installation

### Step 1: Install Test Dependencies

From the `unified-mcp` directory:

```bash
cd whatsapp-mcp/unified-mcp

# Install all dev dependencies including test frameworks
pip install -e ".[dev]"
```

This installs:
- `pytest` - Testing framework
- `pytest-mock` - Enhanced mocking
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage measurement
- `pytest-timeout` - Timeout management
- `pytest-docker` - Docker container management (integration tests)
- `responses` - HTTP request mocking
- `psutil` - Resource monitoring

### Step 2: Verify Installation

```bash
pytest --version
# Expected: pytest 8.0.0+

pytest --co --quiet
# Expected: Collects all test files (may be empty initially)
```

---

## Running Tests

### Quick Commands

**Run all tests** (unit + integration + e2e):
```bash
pytest
```

**Run only unit tests** (fast, <30 seconds):
```bash
pytest tests/unit/
```

**Run only integration tests** (slower, <5 minutes):
```bash
pytest tests/integration/
```

**Run only e2e tests** (slowest, full workflows):
```bash
pytest tests/e2e/
```

**Run specific test file**:
```bash
pytest tests/unit/test_routing.py
```

**Run specific test function**:
```bash
pytest tests/unit/test_routing.py::test_routing_selects_go_backend_when_baileys_down
```

**Run tests matching pattern**:
```bash
pytest -k "routing"
# Runs all tests with "routing" in name

pytest -k "concurrent"
# Runs all concurrency tests
```

---

## Running Tests with Coverage

### Basic Coverage Report

```bash
pytest --cov=. --cov-report=term-missing
```

**Example output**:
```
tests/unit/test_routing.py ......... [ 45%]
tests/unit/test_sync.py .......... [ 90%]
tests/unit/backends/test_health.py .. [100%]

---------- coverage: platform linux, python 3.12.1 -----------
Name                      Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------------
routing.py                  341     60     78     12   82.5%   145-146, 203-205
sync.py                     410     98     92     18   76.8%   89, 234-236, 312-320
backends/health.py          391     80     85     15   79.4%   156-158, 401-410
---------------------------------------------------------------------
TOTAL                      1142    238    255     45   79.5%
```

### HTML Coverage Report (Interactive)

```bash
pytest --cov=. --cov-report=html
firefox htmlcov/index.html
```

This opens an **interactive HTML report** showing:
- Overall coverage percentage
- Per-module breakdown
- Line-by-line coverage (green = covered, red = missing)
- Branch coverage details

### Coverage by Module

**Routing tests only**:
```bash
pytest tests/unit/test_routing.py --cov=routing --cov-report=term-missing
```

**Sync tests only**:
```bash
pytest tests/unit/test_sync.py --cov=sync --cov-report=term-missing
```

**Health tests only**:
```bash
pytest tests/unit/backends/test_health.py --cov=backends/health --cov-report=term-missing
```

---

## Coverage Targets and Thresholds

The test suite enforces these coverage targets:

| Module | Target Coverage | Status |
|--------|----------------|---------|
| **routing.py** | 80% | ⚠️ Currently 0% |
| **sync.py** | 75% | ⚠️ Currently minimal |
| **backends/health.py** | 75% | ⚠️ Currently minimal |
| **Overall** | 70% | ⚠️ Currently ~20% |

**CI/CD will fail** if overall coverage drops below 70%.

---

## Running Tests with Markers

Tests are organized with pytest markers for selective execution:

### Available Markers

```bash
# List all markers
pytest --markers
```

**Common markers**:
- `@pytest.mark.unit` - Unit tests (fast, mocked dependencies)
- `@pytest.mark.integration` - Integration tests (real services)
- `@pytest.mark.e2e` - End-to-end tests (complete workflows)
- `@pytest.mark.slow` - Slow tests (>5 seconds)
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.timeout(seconds)` - Tests with specific timeout

### Running by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only fast tests (exclude slow)
pytest -m "not slow"

# Run async tests only
pytest -m asyncio
```

---

## Verbose and Debug Mode

### Verbose Output

```bash
pytest -v
# Shows individual test names and results

pytest -vv
# Very verbose (shows assertion details)
```

**Example output**:
```
tests/unit/test_routing.py::test_routing_selects_go_backend_when_baileys_down PASSED [ 10%]
tests/unit/test_routing.py::test_routing_prefers_baileys_for_sync_operations PASSED [ 20%]
tests/unit/test_routing.py::test_routing_round_robin_alternates_backends PASSED [ 30%]
```

### Show Print Statements

```bash
pytest -s
# Disables output capture, shows print() statements
```

### Debugging Failed Tests

```bash
# Run only last failed tests
pytest --lf

# Run last failed first, then others
pytest --ff

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb
```

---

## Integration Tests with Docker

Integration tests require Go and Baileys bridges running.

### Option 1: Use Docker Compose (Recommended)

```bash
# Start bridges in background
cd tests/integration
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run integration tests
cd ../..
pytest tests/integration/

# Stop services when done
cd tests/integration
docker-compose down
```

### Option 2: Manual Bridge Startup

```bash
# Terminal 1: Start Go bridge
cd whatsapp-bridge
go run main.go

# Terminal 2: Start Baileys bridge
cd baileys-bridge
npm start

# Terminal 3: Run integration tests
cd whatsapp-mcp/unified-mcp
pytest tests/integration/
```

### Verify Bridges are Running

```bash
# Check Go bridge health
curl http://localhost:8080/health
# Expected: {"status": "healthy", ...}

# Check Baileys bridge health
curl http://localhost:8081/health
# Expected: {"status": "healthy", ...}
```

---

## Running Concurrent Tests

Concurrent tests validate thread safety and race condition handling.

```bash
# Run concurrent tests with default thread count (10)
pytest tests/integration/test_concurrent_operations.py

# Run with verbose output to see thread execution
pytest tests/integration/test_concurrent_operations.py -s -v

# Run only 100-thread concurrency tests
pytest tests/integration/test_concurrent_operations.py -k "100_threads"
```

**These tests**:
- Use `ThreadPoolExecutor` for concurrency
- Use `threading.Barrier` for synchronized starts
- Have timeouts to prevent hangs (30-60 seconds)
- Detect race conditions and resource conflicts

---

## Interpreting Test Results

### Successful Test Run

```
============================= test session starts ==============================
collected 89 items

tests/unit/test_routing.py ..................... [ 23%]
tests/unit/test_sync.py ...................... [ 47%]
tests/unit/backends/test_health.py ........... [ 58%]
tests/integration/test_routing_integration.py ... [ 62%]
tests/integration/test_sync_integration.py ..... [ 68%]
tests/integration/test_concurrent_operations.py .......... [ 80%]
tests/e2e/test_hybrid_workflows.py .................. [100%]

============================== 89 passed in 45.23s ==============================
```

**Key metrics**:
- ✅ All tests passed
- ⏱️ Total time: 45.23s (within 5-minute target)
- 📊 Coverage: (shown if `--cov` flag used)

### Failed Test Run

```
============================= test session starts ==============================
collected 89 items

tests/unit/test_routing.py ...................F. [ 23%]

================================== FAILURES ====================================
_____________ test_routing_selects_go_backend_when_baileys_down ________________

mock_health_monitor = <MagicMock id='140234567890'>

    def test_routing_selects_go_backend_when_baileys_down(mock_health_monitor):
        # Arrange
        mock_health_monitor.set_go_health("healthy")
        mock_health_monitor.set_baileys_health("unhealthy")
        router = Router(health_monitor=mock_health_monitor)

        # Act
        result = router.select_backend(OperationType.SEND_MESSAGE)

        # Assert
>       assert result == Backend.GO
E       AssertionError: assert <Backend.BAILEYS: 'baileys'> == <Backend.GO: 'go'>

tests/unit/test_routing.py:45: AssertionError
===================== 1 failed, 88 passed in 43.12s ============================
```

**Troubleshooting**:
- ❌ Test failed at assertion (line 45)
- 🔍 Expected `Backend.GO` but got `Backend.BAILEYS`
- 🐛 Suggests routing logic not respecting health status

### Timeout Failures

```
================================== FAILURES ====================================
________________________ test_concurrent_operations ____________________________

    @pytest.mark.timeout(30)
    def test_concurrent_operations():
        ...
>       results = [f.result(timeout=5) for f in futures]
E       concurrent.futures.TimeoutError

tests/integration/test_concurrent_operations.py:67: TimeoutError
```

**Causes**:
- Operation took >5 seconds to complete
- Deadlock or resource starvation
- Backend unreachable or slow

---

## Adding New Tests

### Step 1: Choose Test Type

**Unit Test** (tests/unit/):
- Fast execution (<1 second per test)
- Mock all external dependencies
- Test single function or class

**Integration Test** (tests/integration/):
- Tests interaction between components
- Uses real or Docker-based backends
- Slower execution (<30 seconds per test)

**E2E Test** (tests/e2e/):
- Tests complete workflows
- Validates end-to-end behavior
- Slowest execution (<2 minutes per test)

### Step 2: Create Test File

```python
# tests/unit/test_my_feature.py

import pytest
from my_module import my_function

def test_my_function_returns_expected_value():
    """
    Test that my_function returns the expected value.

    Given: Valid input
    When: my_function is called
    Then: Expected value is returned
    """
    # Arrange
    input_value = "test"

    # Act
    result = my_function(input_value)

    # Assert
    assert result == "expected_output"
```

### Step 3: Use Fixtures

```python
def test_with_fixture(sample_messages, test_database):
    """Test using fixtures for test data and database."""
    # sample_messages is automatically provided
    # test_database is initialized and cleaned up automatically

    test_database.insert_messages(sample_messages)
    count = test_database.count_messages()

    assert count == len(sample_messages)
    # Cleanup happens automatically via fixture yield
```

### Step 4: Run Your New Test

```bash
# Run just your new test
pytest tests/unit/test_my_feature.py -v

# Run with coverage
pytest tests/unit/test_my_feature.py --cov=my_module --cov-report=term-missing
```

---

## Common Test Patterns

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("test", "TEST"),
])
def test_uppercase(input, expected):
    """Test uppercase conversion with multiple inputs."""
    assert input.upper() == expected
```

### Testing Exceptions

```python
def test_function_raises_error():
    """Test that function raises expected error."""
    with pytest.raises(ValueError, match="Invalid input"):
        my_function("invalid")
```

### Mocking HTTP Requests

```python
import responses

@responses.activate
def test_api_call():
    """Test API call with mocked HTTP response."""
    responses.add(
        responses.GET,
        "http://localhost:8080/health",
        json={"status": "healthy"},
        status=200
    )

    result = check_backend_health()
    assert result["status"] == "healthy"
```

---

## Continuous Integration

Tests run automatically in CI/CD on every push and pull request.

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests and Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=. --cov-report=xml --cov-report=term-missing
      - uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
      - run: coverage report --fail-under=70
```

**CI/CD checks**:
- ✅ All tests must pass
- 📊 Coverage must be ≥70%
- ⏱️ Unit tests must complete in <30s
- ⏱️ Integration tests must complete in <5min

---

## Troubleshooting

### Problem: "Module not found" errors

**Solution**: Install test dependencies
```bash
pip install -e ".[dev]"
```

### Problem: Integration tests fail with "Connection refused"

**Solution**: Ensure bridges are running
```bash
# Check Go bridge
curl http://localhost:8080/health

# Check Baileys bridge
curl http://localhost:8081/health

# Start with Docker Compose
cd tests/integration && docker-compose up -d
```

### Problem: Slow test execution

**Solution**: Run only unit tests during development
```bash
pytest tests/unit/  # Fast, <30 seconds
```

### Problem: Flaky concurrent tests

**Solution**: Run with increased timeout
```bash
pytest tests/integration/test_concurrent_operations.py --timeout=60
```

### Problem: Coverage not showing my new code

**Solution**: Check coverage paths in pyproject.toml
```toml
[tool.coverage.run]
source = ["."]
omit = ["*/tests/*"]
```

---

## Next Steps

1. **Review existing tests**: Explore `tests/unit/` to see patterns
2. **Run the test suite**: `pytest --cov=. --cov-report=html`
3. **Add tests for your changes**: Follow the patterns in this guide
4. **Verify coverage**: Check HTML report at `htmlcov/index.html`
5. **Commit with confidence**: CI/CD will validate your tests

---

## Additional Resources

- **pytest documentation**: https://docs.pytest.org/
- **pytest-cov guide**: https://pytest-cov.readthedocs.io/
- **Fixture contracts**: See `specs/001-add-comprehensive-test/contracts/conftest_template.py`
- **Data schemas**: See `specs/001-add-comprehensive-test/contracts/test_data_schemas.py`
- **Research findings**: See `specs/001-add-comprehensive-test/research.md`

---

**Quick Start Complete**: 2025-10-12
**Ready for**: Writing your first test!
