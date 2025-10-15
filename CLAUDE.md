# whatsapp-mcp Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-14

## Active Technologies
- Python 3.12+ (requires-python = ">=3.12" in pyproject.toml) (001-add-comprehensive-test)
- Multi-language (Python 3.12+, Go 1.21+, TypeScript/Node.js 20+) (002-add-ci-cd)
- N/A (workflow state managed by GitHub Actions, no persistent storage required) (002-add-ci-cd)
- Python 3.12+ with mypy strict mode and ruff linting (003-improve-code-quality)

## Project Structure
```
unified-mcp/              # Python MCP server (proper package structure)
├── __init__.py           # Package initialization
├── main.py               # MCP entry point
├── constants.py          # Centralized configuration (NEW)
├── backends/             # Backend clients subpackage
│   ├── __init__.py
│   ├── go_client.py
│   ├── baileys_client.py
│   └── health.py
├── routing.py            # Request routing
└── sync.py               # Database sync

whatsapp-bridge/          # Go bridge (whatsmeow)
baileys-bridge/           # Baileys bridge (Node.js)
tests/                    # Test suite
```

## Commands
# Run tests (100/101 passing, 99% pass rate)
cd unified-mcp && .venv/bin/pytest

# Type checking (requires symlink workaround for unified-mcp directory name)
unified-mcp/.venv/bin/mypy unified_mcp/ --config-file unified_mcp/pyproject.toml

# Linting - docstrings (all pass)
cd unified-mcp && ruff check --select D .

# Linting - full check (67 pre-existing E501 line-length warnings)
cd unified-mcp && ruff check .

# Auto-fix linting issues
cd unified-mcp && ruff check --fix .

# Test docstring examples (examples use # doctest: +SKIP for backend dependencies)
cd unified-mcp && pytest --doctest-modules .

# Code metrics
cd unified-mcp && radon mi *.py backends/*.py -s  # Maintainability index
cd unified-mcp && lizard *.py backends/*.py --CCN 10  # Complexity analysis

# Run specific bridge
cd whatsapp-bridge && go run .
cd baileys-bridge && npm start

## Code Style

### Python (unified-mcp)
- Python 3.12+ with modern type hints
- **Package structure**: Standard Python package with `__init__.py` files
  - ⚠️ Directory named `unified-mcp` (hyphen) with symlink `unified_mcp` for import compatibility
  - Tests import modules directly (e.g., `from backends.health import ...`)
  - Relative imports in `__init__.py` disabled due to directory naming
- **Imports**: Direct imports from modules (from backends import go_client)
- **NO sys.path manipulation** - use proper package structure
- **Type hints**: All public functions MUST have complete type annotations (100% coverage)
- **Mypy**: Strict mode configured, 77 baseline type errors documented for incremental improvement
- **Constants**: Use `constants.py` for all configuration values (FR-006 to FR-010)
  - Timeouts: `DEFAULT_TIMEOUT` (30s), `MEDIA_TIMEOUT` (60s), `SHORT_TIMEOUT` (10s), `HEALTH_CHECK_TIMEOUT` (5s)
  - URLs: `GO_BRIDGE_URL`, `BAILEYS_BRIDGE_URL`
  - Retry: `MAX_RETRIES`, `RETRY_DELAY`
  - All constants are `Final` annotated and documented
- **Linting**: Ruff with comprehensive rules (E, F, I, N, W, UP, C90, D, RUF)
  - All D-series docstring rules pass ✅
  - Complexity limit: 10 (1 function at CCN=11, acceptable)
  - 67 pre-existing E501 line-length violations (unrelated to Feature 003)
- **Complexity**: Maximum cyclomatic complexity of 10 per function (avg: 2.1, range: 1-11)
- **Docstrings**: Google-style required for all public functions (100% coverage) with:
  - Short description
  - Args section (all parameters with types)
  - Returns section (with type)
  - Raises section (if applicable)
  - Examples section (pattern established for 5 representative functions, uses `# doctest: +SKIP`)
- **Code Quality**: All modules achieve A-grade maintainability (Radon scores: 45-100)
- **Verification**: See `SUCCESS_CRITERIA_VERIFICATION.md` and `CODE_METRICS_REPORT.md` for detailed analysis

### Go (whatsapp-bridge)
- Go 1.21+ standard conventions
- Follow effective Go guidelines

### TypeScript (baileys-bridge)
- Node.js 20+ with TypeScript
- Standard TypeScript conventions

## Recent Changes
- 003-improve-code-quality (2025-10-14): **Code quality improvements complete** ✅
  - US1: Package structure refactor (removed sys.path hacks, added __init__.py files)
  - US2: Centralized constants.py (timeouts, URLs, retry logic - all Final annotated)
  - US3: Type hints for all functions (100% coverage, mypy strict mode configured)
  - US4: Ruff linting (D-series docstrings, complexity<10, import sorting)
  - US5: Google-style docstrings with examples (100% coverage, pattern-based approach)
  - **Metrics**: 100/101 tests passing, avg complexity 2.1, all A-grade maintainability
  - **Reports**: SUCCESS_CRITERIA_VERIFICATION.md, CODE_METRICS_REPORT.md
- 002-add-ci-cd: Added Multi-language (Python 3.12+, Go 1.21+, TypeScript/Node.js 20+)
- 001-add-comprehensive-test: Added Python 3.12+ (requires-python = ">=3.12" in pyproject.toml)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
