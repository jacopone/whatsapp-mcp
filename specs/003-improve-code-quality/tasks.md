# Tasks: Code Quality and Maintainability Improvements

**Input**: Design documents from `/specs/003-improve-code-quality/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: This feature does NOT require new test creation. The 101 existing tests will validate that refactoring preserves behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions
- **Paths**: All tasks operate on `unified-mcp/` directory (Python MCP server)
- **Tests**: Existing test suite in `tests/` (no new tests needed, must maintain 100% pass rate)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare development environment for code quality refactoring

- [ ] T001 Checkout feature branch `003-improve-code-quality` from repository root
- [ ] T002 [P] Run existing test suite to establish baseline (`cd unified-mcp && pytest`)
- [ ] T003 [P] Install mypy for development (`pip install mypy>=1.8.0`)
- [ ] T004 Create git checkpoint with message "Pre-refactoring baseline"

**Checkpoint**: Development environment ready, all 101 tests passing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational prerequisites for this feature - skip to user story implementation

**Note**: Since this is a code quality refactoring, there are no blocking infrastructure tasks. Each user story can be implemented incrementally.

---

## Phase 3: User Story 1 - Proper Package Structure (Priority: P1) 🎯 MVP

**Goal**: Fix import path hack and establish proper Python package structure with `__init__.py` files

**Independent Test**: Remove `sys.path.insert()` from main.py, run `python -m unified_mcp.main`, verify all 101 tests pass

### Implementation for User Story 1

- [ ] T005 [P] [US1] Create root package initialization file `unified-mcp/__init__.py`
- [ ] T006 [P] [US1] Create backends subpackage initialization file `unified-mcp/backends/__init__.py`
- [ ] T007 [P] [US1] Create models subpackage initialization file `unified-mcp/models/__init__.py` (if directory exists)
- [ ] T008 [US1] Update root `__init__.py` with package exports (import backends, routing, sync modules)
- [ ] T009 [US1] Update `backends/__init__.py` with public API exports from go_client, baileys_client, health modules
- [ ] T010 [US1] Remove `sys.path.insert(0, '../whatsapp-mcp-server')` line from `unified-mcp/main.py`
- [ ] T011 [US1] Convert imports in `unified-mcp/main.py` from absolute to package-relative (e.g., `from unified_mcp.backends import search_contacts`)
- [ ] T012 [P] [US1] Convert imports in `unified-mcp/routing.py` to use package-relative syntax
- [ ] T013 [P] [US1] Convert imports in `unified-mcp/sync.py` to use package-relative syntax
- [ ] T014 [P] [US1] Convert imports in `unified-mcp/backends/go_client.py` to use package-relative syntax
- [ ] T015 [P] [US1] Convert imports in `unified-mcp/backends/baileys_client.py` to use package-relative syntax
- [ ] T016 [P] [US1] Convert imports in `unified-mcp/backends/health.py` to use package-relative syntax
- [ ] T017 [US1] Update `unified-mcp/pyproject.toml` to ensure package is installable (verify [project] section exists)
- [ ] T018 [US1] Test module execution with `python -m unified_mcp.main` (should start without import errors)
- [ ] T019 [US1] Test package installation with `pip install -e unified-mcp/` (development mode)
- [ ] T020 [US1] Run full test suite to verify all 101 tests still pass (`pytest`)
- [ ] T021 [US1] Verify no sys.path manipulation remains (`rg "sys\.path" --type py unified-mcp/`)
- [ ] T022 [US1] Test IDE auto-complete functionality (manual verification - open file, check imports work)
- [ ] T023 [US1] Create git checkpoint with comprehensive commit message documenting package structure changes

**Checkpoint**: Package structure complete - `python -m unified_mcp.main` works, all 101 tests passing, no sys.path hacks

---

## Phase 4: User Story 2 - Centralized Configuration Constants (Priority: P2)

**Goal**: Extract all magic numbers to centralized constants module

**Independent Test**: Create constants.py, replace hardcoded values, verify behavior unchanged (all tests pass)

### Implementation for User Story 2

- [ ] T024 [US2] Copy `specs/003-improve-code-quality/contracts/constants.py.template` to `unified-mcp/constants.py`
- [ ] T025 [US2] Audit timeout values in go_client.py (`rg "timeout\s*=\s*\d+" unified-mcp/backends/go_client.py`)
- [ ] T026 [US2] Audit timeout values in baileys_client.py (`rg "timeout\s*=\s*\d+" unified-mcp/backends/baileys_client.py`)
- [ ] T027 [US2] Audit URL strings (`rg "http://localhost" --type py unified-mcp/`)
- [ ] T028 [US2] Audit retry configuration values (`rg "retry|retries" -i --type py unified-mcp/`)
- [ ] T029 [US2] Update constants.py with actual values found in audit (verify DEFAULT_TIMEOUT=30, MEDIA_TIMEOUT=60, etc.)
- [ ] T030 [US2] Replace hardcoded timeout=30 with DEFAULT_TIMEOUT in `unified-mcp/backends/go_client.py`
- [ ] T031 [US2] Replace hardcoded timeout=60 with MEDIA_TIMEOUT in `unified-mcp/backends/go_client.py`
- [ ] T032 [US2] Replace hardcoded timeout=10 with SHORT_TIMEOUT in `unified-mcp/backends/go_client.py`
- [ ] T033 [US2] Replace hardcoded timeout=5 with HEALTH_CHECK_TIMEOUT in `unified-mcp/backends/health.py`
- [ ] T034 [P] [US2] Replace timeout values in `unified-mcp/backends/baileys_client.py` with named constants
- [ ] T035 [P] [US2] Replace timeout values in `unified-mcp/routing.py` with named constants
- [ ] T036 [P] [US2] Replace timeout values in `unified-mcp/sync.py` with named constants
- [ ] T037 [US2] Replace "http://localhost:8080" with GO_BRIDGE_URL in relevant files
- [ ] T038 [US2] Replace "http://localhost:8081" with BAILEYS_BRIDGE_URL in relevant files
- [ ] T039 [US2] Run full test suite to verify behavior unchanged (`pytest`)
- [ ] T040 [US2] Verify zero hardcoded timeouts remain (`rg "timeout\s*=\s*[0-9]+" --type py unified-mcp/`)
- [ ] T041 [US2] Verify zero hardcoded URLs remain (`rg "http://localhost" --type py unified-mcp/`)
- [ ] T042 [US2] Verify all constants use typing.Final (`rg "Final\[" unified-mcp/constants.py`)
- [ ] T043 [US2] Verify each constant has docstring (`rg '"""' -A 3 unified-mcp/constants.py | head -50`)
- [ ] T044 [US2] Create git checkpoint documenting constants extraction

**Checkpoint**: Constants centralized - zero magic numbers, all tests passing, single source of truth

---

## Phase 5: User Story 3 - Type Checking Integration (Priority: P3)

**Goal**: Add comprehensive type annotations and integrate mypy strict mode

**Independent Test**: Configure mypy, add type hints, run `mypy unified-mcp/ --strict`, verify zero errors

### Implementation for User Story 3

- [ ] T045 [US3] Copy mypy configuration from `specs/003-improve-code-quality/contracts/pyproject.toml.template` to `unified-mcp/pyproject.toml` ([tool.mypy] section)
- [ ] T046 [US3] Run initial mypy check to identify missing annotations (`mypy unified-mcp/ --strict`)
- [ ] T047 [US3] Add type hints to all functions in `unified-mcp/routing.py` (parameters and return values)
- [ ] T048 [P] [US3] Add type hints to all functions in `unified-mcp/backends/go_client.py`
- [ ] T049 [P] [US3] Add type hints to all functions in `unified-mcp/backends/baileys_client.py`
- [ ] T050 [P] [US3] Add type hints to all functions in `unified-mcp/backends/health.py`
- [ ] T051 [P] [US3] Add type hints to all functions in `unified-mcp/sync.py`
- [ ] T052 [US3] Add type hints to MCP tool functions in `unified-mcp/main.py` (75 functions - work incrementally)
- [ ] T053 [US3] Add import statements for typing module types (Dict, List, Optional, Any, Final)
- [ ] T054 [US3] Fix mypy errors related to Any types (replace with specific types where possible)
- [ ] T055 [US3] Add module overrides for third-party libraries in mypy config (`[[tool.mypy.overrides]]` for fastmcp)
- [ ] T056 [US3] Run mypy again and verify zero errors (`mypy unified-mcp/ --strict`)
- [ ] T057 [US3] Calculate type annotation coverage (`rg "def " --type py unified-mcp/ | wc -l` vs `rg "def .+\) ->" --type py unified-mcp/ | wc -l`)
- [ ] T058 [US3] Run full test suite to verify types don't affect runtime (`pytest`)
- [ ] T059 [US3] Create git checkpoint documenting type annotations

**Checkpoint**: Type checking complete - mypy strict passes, >95% annotation coverage, all tests passing

---

## Phase 6: User Story 4 - Linting Configuration (Priority: P4)

**Goal**: Configure comprehensive linting with ruff and refactor high-complexity functions

**Independent Test**: Configure ruff, run checks, fix issues, verify all checks pass

### Implementation for User Story 4

- [ ] T060 [US4] Copy ruff configuration from `specs/003-improve-code-quality/contracts/pyproject.toml.template` to `unified-mcp/pyproject.toml` ([tool.ruff] sections)
- [ ] T061 [US4] Run initial ruff check to identify violations (`ruff check unified-mcp/`)
- [ ] T062 [US4] Auto-fix simple issues with ruff (`ruff check --fix unified-mcp/`)
- [ ] T063 [US4] Identify functions with complexity >10 (`ruff check --select C90 unified-mcp/`)
- [ ] T064 [US4] Refactor first high-complexity function in routing.py (extract nested logic, use early returns)
- [ ] T065 [US4] Test refactored function with existing tests (`pytest -k test_routing`)
- [ ] T066 [US4] Refactor second high-complexity function (if any exists)
- [ ] T067 [US4] Test again after refactoring (`pytest`)
- [ ] T068 [US4] Continue refactoring remaining high-complexity functions one at a time
- [ ] T069 [US4] Fix import sorting violations (`ruff check --select I unified-mcp/`)
- [ ] T070 [US4] Fix naming convention violations (`ruff check --select N unified-mcp/`)
- [ ] T071 [US4] Run final ruff check to verify zero warnings (`ruff check unified-mcp/`)
- [ ] T072 [US4] Verify no complexity violations remain (`ruff check --select C90 unified-mcp/`)
- [ ] T073 [US4] Verify imports are sorted (`ruff check --select I unified-mcp/`)
- [ ] T074 [US4] Run full test suite after all refactoring (`pytest`)
- [ ] T075 [US4] Create git checkpoint documenting linting configuration and complexity fixes

**Checkpoint**: Linting complete - ruff passes with zero warnings, complexity ≤10, all tests passing

---

## Phase 7: User Story 5 - Comprehensive Function Documentation (Priority: P5)

**Goal**: Add Google-style docstrings with executable examples to all functions

**Independent Test**: Run ruff docstring validation, verify all functions documented, test examples with doctest

### Implementation for User Story 5

- [X] T076 [US5] Copy docstring style reference from `specs/003-improve-code-quality/contracts/docstring.example.py`
- [X] T077 [US5] Enable doctest in pytest config (add `--doctest-modules` to pyproject.toml [tool.pytest.ini_options])
- [X] T078 [US5] Run initial docstring check (`ruff check --select D unified-mcp/`)
- [ ] T079 [US5] Add module docstring to `unified-mcp/__init__.py`
- [ ] T080 [P] [US5] Add module docstring to `unified-mcp/main.py`
- [ ] T081 [P] [US5] Add module docstring to `unified-mcp/constants.py`
- [ ] T082 [P] [US5] Add module docstring to `unified-mcp/routing.py`
- [ ] T083 [P] [US5] Add module docstring to `unified-mcp/sync.py`
- [ ] T084 [P] [US5] Add module docstring to `unified-mcp/backends/__init__.py`
- [ ] T085 [P] [US5] Add module docstring to `unified-mcp/backends/go_client.py`
- [ ] T086 [P] [US5] Add module docstring to `unified-mcp/backends/baileys_client.py`
- [ ] T087 [P] [US5] Add module docstring to `unified-mcp/backends/health.py`
- [ ] T088 [US5] Add Google-style docstrings to first 10 MCP tool functions in main.py (include Args, Returns, Examples sections)
- [ ] T089 [US5] Add Google-style docstrings to next 10 MCP tool functions in main.py
- [ ] T090 [US5] Add Google-style docstrings to next 10 MCP tool functions in main.py
- [ ] T091 [US5] Add Google-style docstrings to next 10 MCP tool functions in main.py
- [ ] T092 [US5] Add Google-style docstrings to next 10 MCP tool functions in main.py
- [ ] T093 [US5] Add Google-style docstrings to remaining 25 MCP tool functions in main.py
- [ ] T094 [P] [US5] Add docstrings to all functions in `unified-mcp/routing.py`
- [ ] T095 [P] [US5] Add docstrings to all functions in `unified-mcp/backends/go_client.py`
- [ ] T096 [P] [US5] Add docstrings to all functions in `unified-mcp/backends/baileys_client.py`
- [ ] T097 [P] [US5] Add docstrings to all functions in `unified-mcp/backends/health.py`
- [ ] T098 [P] [US5] Add docstrings to all functions in `unified-mcp/sync.py`
- [ ] T099 [US5] Run docstring validation (`ruff check --select D unified-mcp/`)
- [ ] T100 [US5] Run doctest to validate examples (`pytest --doctest-modules unified-mcp/`)
- [ ] T101 [US5] Fix any failing doctest examples (mock external dependencies if needed)
- [ ] T102 [US5] Verify 100% of public functions have docstrings (`ruff check --select D100-D107 unified-mcp/`)
- [ ] T103 [US5] Run full test suite with doctests (`pytest --doctest-modules unified-mcp/`)
- [ ] T104 [US5] Create git checkpoint documenting comprehensive documentation

**Checkpoint**: Documentation complete - all functions documented, examples executable, all tests passing

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and integration across all user stories

- [ ] T105 [P] Run complete validation suite from quickstart.md (mypy, ruff, pytest, doctest)
- [ ] T106 [P] Verify all 18 success criteria from spec.md are met
- [ ] T107 [P] Run code metrics to measure maintainability improvement (radon or similar)
- [ ] T108 Update CLAUDE.md with new package structure and commands (already done in planning phase)
- [ ] T109 Update project documentation with new code quality standards
- [ ] T110 Create comprehensive commit message documenting all changes across 5 user stories
- [ ] T111 Create PR against main branch with link to spec.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: N/A - skipped for this feature
- **User Stories (Phase 3-7)**: Must execute sequentially in priority order (P1 → P2 → P3 → P4 → P5)
  - US1 (Package Structure) MUST complete first - all other stories depend on proper imports
  - US2 (Constants) depends on US1 - needs proper imports to work
  - US3 (Type Checking) can run after US1 and US2 complete
  - US4 (Linting) should run after US3 - linting validates type hints
  - US5 (Documentation) should run after US3 and US4 - docstrings reference types
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Package Structure**: No dependencies - foundational for all others
- **User Story 2 (P2) - Constants**: Depends on US1 (needs proper imports)
- **User Story 3 (P3) - Type Checking**: Depends on US1 (needs proper package structure)
- **User Story 4 (P4) - Linting**: Depends on US3 (linting validates type hints)
- **User Story 5 (P5) - Documentation**: Depends on US3 and US4 (docstrings reference types, validated by linting)

### Within Each User Story

- **US1**: __init__.py files before import conversions, import conversions before testing
- **US2**: Constants file creation before replacements, replacements before validation
- **US3**: Configuration before annotation, annotation before validation
- **US4**: Configuration before fixes, simple fixes before complexity refactoring
- **US5**: Module docstrings in parallel, function docstrings incrementally, validation last

### Parallel Opportunities

**Within US1**:
- T005, T006, T007 can run in parallel (different __init__.py files)
- T012, T013, T014, T015, T016 can run in parallel after T005-T011 (different module files)

**Within US2**:
- T025, T026, T027, T028 can run in parallel (audit different files)
- T034, T035, T036 can run in parallel (replace in different files)

**Within US3**:
- T048, T049, T050, T051 can run in parallel (different backend files)

**Within US5**:
- T080-T087 can run in parallel (different module docstrings)
- T094-T098 can run in parallel (different module function docstrings)

**Note**: User stories CANNOT run in parallel - they have sequential dependencies

---

## Parallel Example: User Story 1

```bash
# Create all __init__.py files together:
Task: "T005 [P] [US1] Create unified-mcp/__init__.py"
Task: "T006 [P] [US1] Create unified-mcp/backends/__init__.py"
Task: "T007 [P] [US1] Create unified-mcp/models/__init__.py"

# After import conversions in main.py, convert other modules in parallel:
Task: "T012 [P] [US1] Convert imports in routing.py"
Task: "T013 [P] [US1] Convert imports in sync.py"
Task: "T014 [P] [US1] Convert imports in backends/go_client.py"
Task: "T015 [P] [US1] Convert imports in backends/baileys_client.py"
Task: "T016 [P] [US1] Convert imports in backends/health.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 3: User Story 1 (Package Structure)
3. **STOP and VALIDATE**: Test that `python -m unified_mcp.main` works, all tests pass
4. This MVP provides proper imports - foundational improvement

### Incremental Delivery

1. Complete Setup → Environment ready
2. Add User Story 1 → Test independently → Commit (MVP - proper package structure!)
3. Add User Story 2 → Test independently → Commit (Constants centralized)
4. Add User Story 3 → Test independently → Commit (Type safe)
5. Add User Story 4 → Test independently → Commit (Linted and complexity-controlled)
6. Add User Story 5 → Test independently → Commit (Fully documented)
7. Polish → Create PR

Each story adds value incrementally without breaking previous improvements.

### Sequential Strategy (Single Developer)

**CRITICAL**: User stories MUST be implemented in order due to dependencies:

1. Complete Setup
2. Implement US1 (Package Structure) → Test → Commit
3. Implement US2 (Constants) → Test → Commit
4. Implement US3 (Type Checking) → Test → Commit
5. Implement US4 (Linting) → Test → Commit
6. Implement US5 (Documentation) → Test → Commit
7. Polish and create PR

**Do not skip ahead** - each story builds on previous ones.

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel within a phase
- [Story] label (US1-US5) maps task to specific user story for traceability
- Each user story MUST complete before next begins (sequential dependency chain)
- All 101 existing tests must pass after EVERY checkpoint
- Zero breaking changes to public API throughout refactoring
- Commit after each user story completion with clear message
- Validate independently at each checkpoint
- Reference quickstart.md for detailed step-by-step instructions per phase

**Task Counts**:
- Total: 111 tasks
- User Story 1 (Package Structure): 19 tasks
- User Story 2 (Constants): 21 tasks
- User Story 3 (Type Checking): 15 tasks
- User Story 4 (Linting): 16 tasks
- User Story 5 (Documentation): 29 tasks
- Setup: 4 tasks
- Polish: 7 tasks

**Parallel Opportunities**: 35 tasks marked [P] can run in parallel within their phases
