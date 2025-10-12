# whatsapp-mcp Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-12

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
# Run tests
cd unified-mcp && pytest

# Type checking
mypy unified-mcp/ --strict

# Linting
ruff check unified-mcp/

# Auto-fix linting issues
ruff check --fix unified-mcp/

# Test docstring examples
pytest --doctest-modules unified-mcp/

# Run specific bridge
cd whatsapp-bridge && go run .
cd baileys-bridge && npm start

## Code Style

### Python (unified-mcp)
- Python 3.12+ with modern type hints
- **Package structure**: Standard Python package with `__init__.py` files
- **Imports**: Package-relative imports (from .module import) or absolute (from unified_mcp.module import)
- **NO sys.path manipulation** - use proper package structure
- **Type hints**: All public functions MUST have complete type annotations
- **Mypy**: Strict mode enabled, all checks must pass
- **Constants**: Use `unified_mcp.constants` for all configuration values
  - Timeouts: `DEFAULT_TIMEOUT` (30s), `MEDIA_TIMEOUT` (60s), `SHORT_TIMEOUT` (10s), `HEALTH_CHECK_TIMEOUT` (5s)
  - URLs: `GO_BRIDGE_URL`, `BAILEYS_BRIDGE_URL`
  - Retry: `MAX_RETRIES`, `RETRY_DELAY`
- **Linting**: Ruff with comprehensive rules (E, F, I, N, W, UP, C90, D, RUF)
- **Complexity**: Maximum cyclomatic complexity of 10 per function
- **Docstrings**: Google-style required for all public functions with:
  - Short description
  - Args section (all parameters)
  - Returns section
  - Raises section (if applicable)
  - Examples section (executable with doctest)

### Go (whatsapp-bridge)
- Go 1.21+ standard conventions
- Follow effective Go guidelines

### TypeScript (baileys-bridge)
- Node.js 20+ with TypeScript
- Standard TypeScript conventions

## Recent Changes
- 003-improve-code-quality: Code quality improvements (package structure, constants, types, linting, docs)
- 002-add-ci-cd: Added Multi-language (Python 3.12+, Go 1.21+, TypeScript/Node.js 20+)
- 001-add-comprehensive-test: Added Python 3.12+ (requires-python = ">=3.12" in pyproject.toml)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
