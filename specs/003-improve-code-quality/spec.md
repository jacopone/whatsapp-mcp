# Feature Specification: Code Quality and Maintainability Improvements

**Feature Branch**: `003-improve-code-quality`
**Created**: 2025-10-12
**Status**: Draft
**Input**: User description: "Improve code quality and maintainability. Need to: 1) Fix import path hack in main.py (sys.path.insert), use proper Python package structure, 2) Extract magic numbers to constants file (DEFAULT_TIMEOUT=30, MEDIA_TIMEOUT=60, etc), 3) Add type checking with mypy, 4) Add linting with ruff, 5) Ensure all functions have complete docstrings with examples."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Proper Package Structure (Priority: P1)

As a **developer maintaining the WhatsApp MCP codebase**, I need the Python package structure to follow standard conventions so that imports work correctly without path manipulation hacks, making the code more maintainable and easier to test.

**Why this priority**: Import path hacks (`sys.path.insert`) are fragile, break IDE tooling, cause confusion for new developers, and make testing harder. This is foundational - all other code quality improvements depend on having a proper package structure.

**Independent Test**: Can be fully tested by removing the `sys.path.insert` line from `unified-mcp/main.py`, running all imports successfully, and verifying all existing tests still pass without modification.

**Acceptance Scenarios**:

1. **Given** main.py contains `sys.path.insert(0, '../whatsapp-mcp-server')`, **When** developer removes this line and restructures imports to use proper package paths, **Then** all modules import successfully without errors
2. **Given** a proper package structure with `__init__.py` files, **When** developer runs `python -m unified_mcp.main` from project root, **Then** the MCP server starts without import errors
3. **Given** IDE with Python language server, **When** developer opens any module file, **Then** auto-complete and go-to-definition work correctly for all imports
4. **Given** proper relative imports within the package, **When** tests are run via pytest, **Then** all 101 existing tests pass without path manipulation
5. **Given** package installed in development mode (`pip install -e .`), **When** importing from any location, **Then** all package modules are accessible via standard Python import mechanisms

---

### User Story 2 - Centralized Configuration Constants (Priority: P2)

As a **developer adjusting timeout values or other configuration parameters**, I need all magic numbers extracted to a central constants file so that I can change values in one place and understand what each value represents, improving maintainability and reducing errors.

**Why this priority**: Magic numbers (30, 60, 10, 5) scattered throughout the codebase make it hard to understand what they represent, difficult to adjust globally, and error-prone when changes are needed. After package structure is fixed, this is the next most impactful change for maintainability.

**Independent Test**: Can be fully tested by creating a constants module, moving all magic numbers there, updating all usages to reference the constants, and verifying no functional behavior changes occur.

**Acceptance Scenarios**:

1. **Given** timeout values hardcoded as integers throughout the codebase, **When** developer creates `constants.py` with named constants (DEFAULT_TIMEOUT, MEDIA_TIMEOUT, HEALTH_CHECK_TIMEOUT), **Then** all magic numbers are replaced with named constant references
2. **Given** a constants file with clear names and documentation, **When** developer needs to adjust a timeout value, **Then** they change it in one place and all usages update automatically
3. **Given** constants file with docstrings explaining each value's purpose, **When** new developer reads the code, **Then** they understand why each timeout value was chosen
4. **Given** tests using the constants, **When** tests run, **Then** behavior is identical to previous hardcoded values
5. **Given** URL endpoints hardcoded as strings, **When** developer moves them to constants, **Then** all endpoint references use the named constants

---

### User Story 3 - Type Checking Integration (Priority: P3)

As a **developer adding new code or refactoring existing code**, I need static type checking with mypy integrated into the development workflow so that type errors are caught before runtime, reducing bugs and improving code quality.

**Why this priority**: Type checking catches entire categories of bugs during development rather than runtime. Since the CI/CD pipeline already exists (Feature 002), integrating mypy is straightforward and provides immediate value without blocking other improvements.

**Independent Test**: Can be fully tested by configuring mypy, adding type annotations to all functions, running mypy check, and verifying it passes with zero errors.

**Acceptance Scenarios**:

1. **Given** functions without type annotations, **When** developer adds type hints to parameters and return values, **Then** mypy validates the types correctly
2. **Given** mypy configured in pyproject.toml, **When** developer runs `mypy src/`, **Then** all type inconsistencies are reported
3. **Given** CI/CD pipeline with code-quality job, **When** PR is submitted, **Then** mypy check runs automatically and blocks merge on type errors
4. **Given** a function with incorrect type usage, **When** mypy runs, **Then** it reports the specific line and type mismatch
5. **Given** strict mypy settings enabled, **When** code is checked, **Then** all implicit `Any` types and untyped function definitions are flagged

---

### User Story 4 - Linting Configuration (Priority: P4)

As a **developer writing or reviewing code**, I need consistent linting with ruff properly configured so that code style is enforced automatically, reducing review friction and maintaining consistent code quality across the codebase.

**Why this priority**: While CI/CD already includes ruff, it may not be fully configured with project-specific rules. Proper linting configuration ensures consistency but is less critical than structural issues (P1-P2) and type safety (P3).

**Independent Test**: Can be fully tested by configuring ruff rules in pyproject.toml, running ruff checks on all code, fixing reported issues, and verifying the codebase passes all linting rules.

**Acceptance Scenarios**:

1. **Given** ruff configured with comprehensive rule set in pyproject.toml, **When** developer runs `ruff check .`, **Then** all style violations are reported
2. **Given** inconsistent import ordering in files, **When** developer runs `ruff check --select I`, **Then** import order violations are identified and auto-fixable
3. **Given** code with complexity violations, **When** ruff runs with complexity rules enabled, **Then** functions exceeding complexity limits are flagged
4. **Given** docstring format inconsistencies, **When** ruff runs with docstring rules, **Then** missing or malformed docstrings are identified
5. **Given** pre-commit hook configured, **When** developer commits code, **Then** ruff automatically formats and checks code before commit

---

### User Story 5 - Comprehensive Function Documentation (Priority: P5)

As a **developer using or maintaining the codebase**, I need all functions to have complete docstrings with parameter descriptions, return values, and usage examples so that I can understand how to use functions correctly without reading implementation details.

**Why this priority**: Documentation is important for long-term maintainability but can be added incrementally after structural and tooling improvements are in place. It's the lowest priority because missing docs don't cause immediate bugs.

**Independent Test**: Can be fully tested by running docstring validation (ruff with docstring rules), verifying all public functions have complete docstrings, and checking that examples in docstrings are valid and executable.

**Acceptance Scenarios**:

1. **Given** a function without docstring, **When** developer adds docstring following Google or NumPy style, **Then** function purpose, parameters, return value, and exceptions are documented
2. **Given** docstring with usage example, **When** developer reads the docstring, **Then** they can understand how to call the function without reading implementation
3. **Given** docstring validation enabled in ruff, **When** code is checked, **Then** missing or incomplete docstrings are flagged
4. **Given** functions with complex parameters, **When** docstrings include type information and constraints, **Then** developers know valid input ranges and types
5. **Given** all public API functions documented, **When** new developer onboards, **Then** they can understand the codebase structure and usage without extensive code reading

---

### Edge Cases

- What happens when existing imports break during package restructure? → Use incremental refactoring with git commits after each working state to enable rollback
- How does system handle constants that need different values in test vs. production? → Use environment variables or configuration file overrides for environment-specific values
- What if mypy reports false positives on third-party library types? → Use type: ignore comments with explanation or create type stubs for problematic libraries
- How are docstring examples validated? → Use doctest module to execute examples as tests, ensuring they remain valid
- What if ruff rules conflict with existing code style? → Configure ruff to match current style first, then incrementally tighten rules with team approval
- How are breaking changes to public APIs handled during refactoring? → Use deprecation warnings for changed signatures, maintain backward compatibility for at least one version

## Requirements *(mandatory)*

### Functional Requirements

**Package Structure (User Story 1)**:
- **FR-001**: System MUST have a proper Python package structure with `__init__.py` files in all package directories
- **FR-002**: System MUST use relative imports within the package (e.g., `from .backends import go_client`)
- **FR-003**: System MUST be installable via `pip install -e .` in development mode without manual path manipulation
- **FR-004**: System MUST remove all `sys.path.insert` statements from code
- **FR-005**: System MUST organize code into logical subpackages (unified_mcp.backends, unified_mcp.models, etc.)

**Constants and Configuration (User Story 2)**:
- **FR-006**: System MUST define all timeout values as named constants in a constants module
- **FR-007**: System MUST define all URL endpoints as named constants
- **FR-008**: System MUST document each constant with a docstring explaining its purpose and rationale for the value
- **FR-009**: System MUST group related constants (timeouts, URLs, limits) in logical sections
- **FR-010**: Constants MUST be immutable (use Final type annotation)

**Type Checking (User Story 3)**:
- **FR-011**: System MUST have type annotations on all function parameters and return values
- **FR-012**: System MUST pass mypy strict mode checks with zero errors
- **FR-013**: System MUST configure mypy in pyproject.toml with appropriate settings
- **FR-014**: System MUST use proper type hints for complex types (Dict, List, Optional, Union)
- **FR-015**: System MUST integrate mypy check into CI/CD pipeline (already exists in Feature 002, needs verification)

**Linting (User Story 4)**:
- **FR-016**: System MUST configure ruff with comprehensive rule set in pyproject.toml
- **FR-017**: System MUST pass ruff checks with zero warnings (select appropriate rules first)
- **FR-018**: System MUST use ruff for import sorting and formatting
- **FR-019**: System MUST enforce maximum line length (existing: 100 characters)
- **FR-020**: System MUST enforce maximum function complexity of 10 (McCabe cyclomatic complexity)

**Documentation (User Story 5)**:
- **FR-021**: System MUST have docstrings for all public functions using Google or NumPy style
- **FR-022**: Docstrings MUST include description, parameters (with types), return value, and raised exceptions
- **FR-023**: Docstrings MUST include at least one usage example for non-trivial functions
- **FR-024**: System MUST validate docstrings with ruff docstring rules (D-series)
- **FR-025**: Examples in docstrings MUST be executable and tested via doctest

### Key Entities

- **Constants Module**: Central location for all configuration values (timeouts, URLs, limits, magic numbers)
- **Package Structure**: Hierarchical organization of Python modules with proper __init__.py files enabling standard imports
- **Type Annotations**: Inline metadata describing expected types for function parameters, return values, and variables
- **Docstring**: Structured documentation block for functions including description, parameters, returns, examples

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Package Structure**:
- **SC-001**: Developer can run `python -m unified_mcp.main` from project root without errors
- **SC-002**: All 101 existing tests pass without any sys.path modifications
- **SC-003**: IDE auto-complete and go-to-definition work for 100% of internal imports

**Constants and Configuration**:
- **SC-004**: Zero hardcoded timeout values remain in HTTP request calls
- **SC-005**: Developer can change a timeout value by editing one line in constants file
- **SC-006**: 100% of magic numbers (timeout values, URL strings, retry counts) are defined as named constants

**Type Checking**:
- **SC-007**: Mypy strict mode check passes with zero errors
- **SC-008**: All public functions (75 MCP tools + internal functions) have complete type annotations
- **SC-009**: Type errors caught by mypy in CI/CD before code review

**Linting**:
- **SC-010**: Ruff check passes with zero warnings on full codebase
- **SC-011**: Code formatting is consistent across all files (enforced by ruff)
- **SC-012**: Import statements are sorted consistently (enforced by ruff)

**Documentation**:
- **SC-013**: 100% of public functions have docstrings meeting ruff D-series rules
- **SC-014**: All MCP tool functions (75 tools) have usage examples in docstrings
- **SC-015**: New developers can understand function usage from docstrings alone (measured via onboarding feedback)

**Overall Quality**:
- **SC-016**: Code maintainability index improves by at least 15% (measured by radon or similar tool)
- **SC-017**: PR review comments related to code style and documentation reduce by 70%
- **SC-018**: Time to onboard new developers reduces by 40% (measured by time to first meaningful PR)

## Assumptions

- Existing CI/CD pipeline from Feature 002 is functional and can be extended with additional checks
- Current test suite (101 tests) has good coverage and can validate refactoring doesn't break functionality
- Team agrees on Google-style docstrings (alternative: NumPy-style if preferred)
- Maximum line length of 100 characters (already configured) is acceptable
- Type checking will use Python 3.12+ type hints (existing requirement from pyproject.toml)
- Ruff is preferred over black+flake8+isort combination (already configured in CI/CD)
- Package name will be `unified_mcp` (underscore convention for importable packages)
- Refactoring will be done incrementally with each user story as a separate PR to minimize risk

## Out of Scope

- Rewriting existing logic or algorithms (only refactoring for structure/quality)
- Adding new features or functionality
- Performance optimization (unless type hints enable significant improvements)
- Database schema changes
- API contract changes (maintain backward compatibility)
- Refactoring Go or TypeScript bridges (focus is on Python codebase only)
- Comprehensive test suite expansion (test coverage improvements are Feature 001, already complete)

## Dependencies

- Feature 002 (CI/CD Pipeline) must be complete and functional
- Python 3.12+ environment (already required by pyproject.toml)
- Development tools: mypy, ruff, pytest, doctest (can be added to dev dependencies)
- No external API or service dependencies
