# Tasks: Automated CI/CD Pipeline with Quality Gates

**Input**: Design documents from `/specs/002-add-ci-cd/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: NOT REQUESTED - No test tasks included (infrastructure feature, validation via actual PR testing)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions
- **Repository root**: `.github/workflows/`, configuration files
- **Python project**: `unified-mcp/` (pyproject.toml, pytest.ini)
- **Configuration**: `.codecov.yml`, `.semgrepignore`, etc.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for CI/CD workflows

- [ ] T001 Create `.github/workflows/` directory if not exists
- [ ] T002 [P] Install pytest-rerunfailures in unified-mcp/pyproject.toml dev dependencies

**Checkpoint**: Basic structure ready for workflow files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core workflow files and configurations that ALL user stories depend on

**⚠️ CRITICAL**: No user story implementation can begin until these workflow files exist

- [ ] T003 [P] Create `.github/workflows/ci.yml` from contracts/ci-workflow.yml specification
- [ ] T004 [P] Create `.github/workflows/security.yml` from contracts/security-workflow.yml specification
- [ ] T005 [P] Create `.codecov.yml` configuration file with 70% threshold

**Checkpoint**: Foundation ready - workflow files exist, user story features can now be added

---

## Phase 3: User Story 1 - Automated Test Execution on Pull Requests (Priority: P1) 🎯 MVP

**Goal**: Automatically run all tests when PR created, display real-time status, retry flaky tests

**Independent Test**: Create test PR with code changes, verify tests execute within 2 minutes, see "Tests: Passed" status with test count

### Implementation for User Story 1

- [ ] T006 [US1] Configure pytest retry in unified-mcp/pytest.ini (`addopts = --reruns 3 --reruns-delay 1`)
- [ ] T007 [US1] Verify ci.yml test jobs include `--reruns 3` flags for Python 3.12 and 3.13 matrix
- [ ] T008 [US1] Add status update configuration to ci.yml (ensure `permissions: security-events: write`)
- [ ] T009 [US1] Configure test notification in ci.yml (GitHub default PR notifications)
- [ ] T010 [US1] Test by creating PR: verify tests execute within 2 minutes, status shows "Tests: Running" → "Tests: Passed"

**Checkpoint**: US1 complete - Tests automatically execute on PRs with retry logic, status visible

---

## Phase 4: User Story 2 - Code Quality Validation (Priority: P2)

**Goal**: Automatically verify code meets quality standards (formatting, style, type safety, security)

**Independent Test**: Create PR with intentional formatting error, style violation, type error, and known vulnerable dependency; verify each detected separately

### Implementation for User Story 2

- [ ] T011 [P] [US2] Verify ci.yml includes ruff format check step
- [ ] T012 [P] [US2] Verify ci.yml includes ruff linting step
- [ ] T013 [P] [US2] Verify ci.yml includes mypy type checking step
- [ ] T014 [P] [US2] Verify security.yml includes Semgrep SAST step
- [ ] T015 [P] [US2] Verify security.yml includes Trivy dependency scanning step
- [ ] T016 [P] [US2] Verify security.yml includes Gitleaks secret detection step
- [ ] T017 [US2] Configure SARIF upload to GitHub Security tab in security.yml (already in specification)
- [ ] T018 [US2] Test by creating PR with quality issues: verify each issue type detected and reported

**Checkpoint**: US2 complete - Code quality and security checks run on PRs, findings reported

---

## Phase 5: User Story 3 - Multi-Language Build Verification (Priority: P3)

**Goal**: Verify changes compile and build successfully across Python, Go, TypeScript

**Independent Test**: Create PRs with build errors in each language, verify each build process runs and reports failures

### Implementation for User Story 3

- [ ] T019 [P] [US3] Verify ci.yml includes Go build step with `go build -v ./...` in whatsapp-bridge/
- [ ] T020 [P] [US3] Verify ci.yml includes Go test step with `go test -v ./...` in whatsapp-bridge/
- [ ] T021 [P] [US3] Verify ci.yml includes TypeScript build step with `npm run build` in baileys-bridge/
- [ ] T022 [P] [US3] Verify ci.yml includes TypeScript test step with `npm test` in baileys-bridge/
- [ ] T023 [P] [US3] Verify Python package build implicit in pytest execution (import validation)
- [ ] T024 [US3] Test by creating PRs with build errors: verify Go, TypeScript, Python builds fail appropriately

**Checkpoint**: US3 complete - Build verification runs for all three languages on PRs

---

## Phase 6: User Story 4 - Test Coverage Monitoring and Enforcement (Priority: P4)

**Goal**: Measure test coverage, prevent merging if coverage drops below 70%, show coverage trends

**Independent Test**: Create two PRs - one maintaining coverage above 70% (passes), one dropping below 70% (fails with specific metrics)

### Implementation for User Story 4

- [ ] T025 [US4] Sign up for Codecov account and add repository at https://codecov.io
- [ ] T026 [US4] Add CODECOV_TOKEN to GitHub repository secrets (Settings → Secrets → Actions) if private repo
- [ ] T027 [US4] Verify ci.yml includes Codecov upload step with `continue-on-error: true` and `fail_ci_if_error: false`
- [ ] T028 [US4] Verify ci.yml includes coverage threshold check with `--cov-fail-under=70`
- [ ] T029 [US4] Verify .codecov.yml has project.target: 70% and patch.target: 70%
- [ ] T030 [US4] Test by creating PR that maintains coverage: verify "Coverage: Passed" status
- [ ] T031 [US4] Test by creating PR that drops coverage: verify "Coverage: Failed" status with percentage shown

**Checkpoint**: US4 complete - Coverage calculated, 70% threshold enforced, trends visible

---

## Phase 7: User Story 5 - Automated Merge Protection (Priority: P5)

**Goal**: Prevent merging PRs with failing checks, allow maintainer override

**Independent Test**: Attempt to merge PRs with various check statuses, verify merge only allowed when all pass or with override

### Implementation for User Story 5

- [ ] T032 [US5] Configure branch protection for `main` branch (Settings → Branches → Add rule)
- [ ] T033 [US5] Enable "Require status checks to pass before merging" in branch protection
- [ ] T034 [US5] Enable "Require branches to be up to date before merging" in branch protection
- [ ] T035 [US5] Add required status checks to branch protection:
  - `test (Python 3.12)`
  - `test (Python 3.13)`
  - `code-quality`
  - `build-go`
  - `build-typescript`
  - `sast`
  - `dependencies`
  - `secrets`
  - `codecov/project`
- [ ] T036 [P] [US5] Repeat branch protection configuration for `develop` branch if used
- [ ] T037 [US5] Test by creating PR with passing checks: verify "Ready to merge" status
- [ ] T038 [US5] Test by creating PR with failing check: verify merge blocked with message listing failed checks
- [ ] T039 [US5] Test maintainer override: verify admin can override merge block (optional setting)

**Checkpoint**: US5 complete - Branch protection prevents bad merges, all checks enforced

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Configuration tuning, optimization, and documentation

- [ ] T040 [P] Create `.semgrepignore` file to exclude tests/ from security scanning
- [ ] T041 [P] Create `.trivyignore` file template (empty initially, for future false positives)
- [ ] T042 [P] Create `.gitleaks.toml` configuration if needed (optional, default rules sufficient)
- [ ] T043 [P] Add dependency caching to ci.yml for pip (already in specification, verify present)
- [ ] T044 [P] Add dependency caching to ci.yml for Go modules (already in specification, verify present)
- [ ] T045 [P] Add dependency caching to ci.yml for npm (already in specification, verify present)
- [ ] T046 [P] Configure concurrency groups in workflows for automatic cancellation of obsolete runs (already in specification, verify present)
- [ ] T047 [P] Configure draft PR skipping in workflows with `if: github.event.pull_request.draft == false` (already in specification, verify present)
- [ ] T048 [P] Verify workflow timeout settings (ci.yml: 15 min, security.yml: 10 min)
- [ ] T049 Validate quickstart.md by following implementation steps
- [ ] T050 Monitor first 5 PRs for performance: verify execution times < 10 minutes for 95% of runs
- [ ] T051 Monitor first 2 weeks for false positives: tune Semgrep rules if noise > 20%
- [ ] T052 [P] Update project documentation with CI/CD pipeline information (if project README exists)

**Checkpoint**: Polish complete - All optimizations applied, documentation updated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational (Phase 2) completion
  - User stories can proceed in parallel after Phase 2 (if staffed)
  - Or sequentially in priority order: P1 (US1) → P2 (US2) → P3 (US3) → P4 (US4) → P5 (US5)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1 - Test Execution)**: Can start after Phase 2 - No dependencies on other stories
- **US2 (P2 - Code Quality)**: Can start after Phase 2 - Independent of US1
- **US3 (P3 - Build Verification)**: Can start after Phase 2 - Independent of US1, US2
- **US4 (P4 - Coverage)**: Can start after Phase 2 - Independent of other stories (uses existing test infrastructure)
- **US5 (P5 - Merge Protection)**: Depends on US1, US2, US3, US4 - Requires all check names to exist before configuring branch protection

### Within Each User Story

- Tests (N/A - no test tasks for infrastructure feature)
- Configuration before verification
- Verification before moving to next story
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
- T001 and T002 can run in parallel

**Phase 2 (Foundational)**:
- T003, T004, T005 can all run in parallel (different files)

**Phase 3 (US1)**:
- Sequential execution required (configuration, then verification)

**Phase 4 (US2)**:
- T011-T016 can run in parallel (verification of different workflow sections)

**Phase 5 (US3)**:
- T019-T023 can run in parallel (verification of different build sections)

**Phase 6 (US4)**:
- T025-T029 are sequential (Codecov setup, then configuration)

**Phase 7 (US5)**:
- T032-T036 are sequential (branch protection setup)
- T036 can run parallel with T037-T039 if develop branch exists

**Phase 8 (Polish)**:
- T040-T048, T052 can all run in parallel (different configuration files)
- T049-T051 are sequential (monitoring tasks)

**Across User Stories** (after Phase 2 completes):
- US1, US2, US3, US4 can all be worked on in parallel
- US5 must wait until US1-US4 complete (needs all check names)

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all foundational workflow creation together:
Task: "Create .github/workflows/ci.yml from contracts/ci-workflow.yml specification"
Task: "Create .github/workflows/security.yml from contracts/security-workflow.yml specification"
Task: "Create .codecov.yml configuration file with 70% threshold"
```

## Parallel Example: User Story 2 (Code Quality)

```bash
# Launch all verification checks together:
Task: "Verify ci.yml includes ruff format check step"
Task: "Verify ci.yml includes ruff linting step"
Task: "Verify ci.yml includes mypy type checking step"
Task: "Verify security.yml includes Semgrep SAST step"
Task: "Verify security.yml includes Trivy dependency scanning step"
Task: "Verify security.yml includes Gitleaks secret detection step"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002) - 10 minutes
2. Complete Phase 2: Foundational (T003-T005) - 30 minutes
3. Complete Phase 3: User Story 1 (T006-T010) - 45 minutes
4. **STOP and VALIDATE**: Create test PR, verify tests run with retry, status visible
5. **MVP COMPLETE** - Basic CI/CD pipeline functional

**Estimated MVP time**: 1.5 hours

### Incremental Delivery

1. **MVP** (Phase 1-3): Test execution with retry → Deploy/Validate
2. **+ US2** (Phase 4): Add code quality + security scanning → Deploy/Validate (2 hours total)
3. **+ US3** (Phase 5): Add multi-language builds → Deploy/Validate (2.5 hours total)
4. **+ US4** (Phase 6): Add coverage enforcement → Deploy/Validate (3.5 hours total)
5. **+ US5** (Phase 7): Add merge protection → Deploy/Validate (4 hours total)
6. **Polish** (Phase 8): Optimize and document → Final deployment (5 hours total)

### Parallel Team Strategy

With multiple developers (after Phase 2 completes):

**Single developer** (recommended for infrastructure feature):
- Sequential implementation: US1 → US2 → US3 → US4 → US5 → Polish
- Estimated total: 5-6 hours

**Two developers** (if needed):
- Dev A: US1 → US3 → US5 (test execution, builds, merge protection)
- Dev B: US2 → US4 → Polish (code quality, coverage, optimization)
- Coordination required for US5 (needs check names from US1-US4)

**Three+ developers** (not recommended for this feature):
- Infrastructure configuration benefits from single ownership
- Too many cooks spoil the workflow YAML

---

## Implementation Notes

### Critical Success Factors

1. **Use contracts as templates**: Copy contracts/ci-workflow.yml and contracts/security-workflow.yml exactly (already correct specifications)
2. **Test incrementally**: After each user story, create a test PR to verify that story works
3. **Monitor performance**: Track workflow execution times from first PR onward
4. **Tune security scans**: Expect some Semgrep false positives initially, tune over 2 weeks
5. **Fail-open is critical**: External service failures (Codecov) must not block PRs

### Common Pitfalls to Avoid

1. **Don't skip foundational phase**: Workflow files must exist before any story configuration
2. **Don't forget matrix strategy**: Python testing needs both 3.12 and 3.13
3. **Don't hard-fail on Codecov**: Must use `continue-on-error: true` and `fail_ci_if_error: false`
4. **Don't configure branch protection too early**: Wait until US1-US4 complete (all check names exist)
5. **Don't over-tune initially**: Let security scans run 2 weeks before adjusting rules

### Validation Checkpoints

After each phase, verify:

- **Phase 1**: Directories exist, dependencies installed
- **Phase 2**: Workflows visible in .github/workflows/, no YAML errors
- **Phase 3**: Create PR, tests run with retry, status shows within 2 min
- **Phase 4**: Security scans run, findings appear in Security tab
- **Phase 5**: Builds run for all three languages, failures detected
- **Phase 6**: Coverage report appears, 70% threshold enforced
- **Phase 7**: Branch protection blocks failing PRs, allows passing PRs
- **Phase 8**: All optimizations present, documentation complete

### File Mapping

| Task | File Path | User Story |
|------|-----------|------------|
| T001 | `.github/workflows/` (directory) | Setup |
| T002 | `unified-mcp/pyproject.toml` | Setup |
| T003 | `.github/workflows/ci.yml` | Foundational |
| T004 | `.github/workflows/security.yml` | Foundational |
| T005 | `.codecov.yml` | Foundational |
| T006 | `unified-mcp/pytest.ini` | US1 |
| T007-T010 | `.github/workflows/ci.yml` (verification) | US1 |
| T011-T018 | `.github/workflows/ci.yml`, `.github/workflows/security.yml` (verification) | US2 |
| T019-T024 | `.github/workflows/ci.yml` (verification) | US3 |
| T025-T031 | Codecov UI, `.codecov.yml`, `.github/workflows/ci.yml` (verification) | US4 |
| T032-T039 | GitHub Settings → Branches (UI configuration) | US5 |
| T040-T048 | Various config files (`.semgrepignore`, etc.) | Polish |
| T049-T052 | Documentation, monitoring | Polish |

---

## Success Criteria Mapping

This task list delivers all 11 success criteria from spec.md:

- **SC-001** (100% PRs trigger checks in 2 min): US1 (T006-T010)
- **SC-002** (95% get results in 10 min): US1, US2, US3 (parallel execution)
- **SC-003** (Zero failing tests merged): US1 + US5 (T010 + T032-T039)
- **SC-004** (Coverage ≥70%): US4 (T025-T031)
- **SC-005** (Code quality issues detected): US2 (T011-T018)
- **SC-006** (Build breakages detected): US3 (T019-T024)
- **SC-007** (80% reduction in style feedback): US2 (T011-T013)
- **SC-008** (30% faster PR to merge): US1-US5 combined (automation)
- **SC-009** (95% developer confidence): US1-US4 combined (comprehensive checks)
- **SC-010** (Zero broken main/develop): US5 (T032-T039 branch protection)
- **SC-011** (Security vulnerabilities detected): US2 (T014-T016)

---

## Estimated Effort

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|---------------|--------------|
| Phase 1: Setup | T001-T002 | 10 minutes | None |
| Phase 2: Foundational | T003-T005 | 30 minutes | Phase 1 |
| Phase 3: US1 (Test Execution) | T006-T010 | 45 minutes | Phase 2 |
| Phase 4: US2 (Code Quality) | T011-T018 | 45 minutes | Phase 2 |
| Phase 5: US3 (Builds) | T019-T024 | 30 minutes | Phase 2 |
| Phase 6: US4 (Coverage) | T025-T031 | 60 minutes | Phase 2 |
| Phase 7: US5 (Merge Protection) | T032-T039 | 30 minutes | Phase 3-6 |
| Phase 8: Polish | T040-T052 | 60 minutes | Phase 7 |
| **Total** | **52 tasks** | **5 hours** | Sequential |

**MVP (Phase 1-3)**: 1.5 hours
**Full Feature (All phases)**: 5 hours

---

## Notes

- [P] tasks = different files or verification steps, can run concurrently
- [Story] label maps task to specific user story for traceability (US1-US5)
- Each user story should be independently verifiable by creating test PRs
- Contracts (ci-workflow.yml, security-workflow.yml) are complete specifications - use them as templates
- No test code tasks - this is infrastructure configuration, validated via actual PR testing
- Commit after each logical group of tasks (per phase recommended)
- Stop at any checkpoint to validate story independently
- Follow quickstart.md for detailed step-by-step instructions
