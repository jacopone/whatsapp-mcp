# Implementation Plan: Automated CI/CD Pipeline with Quality Gates

**Branch**: `002-add-ci-cd` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-add-ci-cd/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement automated CI/CD pipeline using GitHub Actions to enforce quality gates on pull requests. The system will execute tests (with auto-retry for flaky tests), perform code quality validation (formatting, style, type checking), run security scanning (SAST, dependency vulnerabilities, secret detection), verify multi-language builds (Go, TypeScript, Python), calculate test coverage with 70% minimum threshold, and block merges when checks fail. The pipeline operates within GitHub Actions free tier limits and uses existing GitHub UI for monitoring.

## Technical Context

**Language/Version**: Multi-language (Python 3.12+, Go 1.21+, TypeScript/Node.js 20+)
**Primary Dependencies**:
- GitHub Actions (workflow execution platform)
- pytest with pytest-cov and pytest-rerunfailures (Python testing)
- ruff (Python linting/formatting)
- mypy (Python type checking)
- **Semgrep** (SAST - static application security testing)
- **Trivy** (dependency vulnerability scanning)
- **Gitleaks** (secret detection)
- Codecov (test coverage reporting)
- Go toolchain (go test, go build)
- TypeScript toolchain (tsc, npm test)

**Storage**: N/A (workflow state managed by GitHub Actions, no persistent storage required)

**Testing**: pytest (Python), go test (Go), npm test (TypeScript) with auto-retry on failure (3 retries)

**Target Platform**: GitHub-hosted runners (Ubuntu latest, supports all three languages)

**Project Type**: Single repository with multi-language components (Python MCP server, Go bridge, TypeScript bridge)

**Performance Goals**:
- Check trigger latency: <2 minutes from PR creation
- Total check execution: <10 minutes for 95% of PRs
- Status update propagation: <30 seconds

**Constraints**:
- GitHub Actions free tier: 2000 minutes/month (private repos) or unlimited (public repos)
- Support 10-20 PRs per day within free tier
- External service retries: 3 attempts × 30 seconds = 90 seconds max wait
- Test retries: 3 attempts per failed test

**Scale/Scope**:
- Current test suite: 101 tests
- Expected workflow runs: 10-20 per day
- Protected branches: main, develop
- Check types: 7 (tests, formatting, style, types, security, build, coverage)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASSED

**Note**: No project constitution file exists yet (constitution.md is template). This feature adds CI/CD infrastructure which is meta-level (enforces future constitution principles). No violations to check.

**Recommendations for future constitution**:
- Define test coverage minimums (this feature implements 70%)
- Define code quality standards (this feature implements ruff + mypy)
- Define security scanning requirements (this feature implements SAST + secrets)
- Define acceptable complexity limits (this feature will enforce them)

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
.github/
├── workflows/
│   ├── ci.yml                    # Main CI/CD workflow (NEW - this feature)
│   └── security.yml              # Security scanning workflow (NEW - this feature)
└── dependabot.yml                # Dependency update automation (OPTIONAL)

unified-mcp/                       # Python MCP server (existing)
├── src/
│   ├── routing.py                # 83.80% coverage
│   ├── sync.py                   # 82.48% coverage
│   └── backends/
│       └── health.py             # 87.66% coverage
├── tests/
│   ├── unit/                     # 101 existing tests
│   ├── integration/
│   └── e2e/
├── pyproject.toml                # Dependencies, test config
└── .coverage                     # Coverage data file

whatsapp-bridge/                   # Go backend (existing)
├── go.mod
├── go.sum
├── main.go
└── [Go source files]

baileys-bridge/                    # TypeScript backend (existing)
├── package.json
├── tsconfig.json
├── src/
└── tests/

.codecov.yml                       # Codecov configuration (NEW - this feature)
pytest.ini                         # pytest retry configuration (MODIFIED - this feature)
```

**Structure Decision**: This is a single repository with multi-language components. CI/CD workflows will be added to `.github/workflows/` directory. The existing test infrastructure (pytest for Python, go test for Go, npm test for TypeScript) will be enhanced with retry logic and integrated into GitHub Actions workflows. No changes to source code structure required - only workflow configuration files and tool configurations.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

N/A - No constitution violations. This feature adds infrastructure configuration (YAML workflows) rather than application code.

---

## Implementation Phases

### Phase 0: Research ✅ COMPLETE

**Status**: COMPLETE
**Output**: `research.md`

**Resolved Clarifications**:
1. ✅ Security scanning tool selection → **Semgrep + Trivy + Gitleaks** (free, comprehensive)
2. ✅ Test retry implementation → **pytest-rerunfailures** (3 retries, 1s delay)
3. ✅ External service retry strategy → **GitHub Actions retry with fail-open** (3 attempts, 30s intervals)
4. ✅ Coverage reporting strategy → **Codecov with fail-open** (70% threshold)
5. ✅ Workflow organization → **Split into ci.yml and security.yml** (parallel execution)
6. ✅ Branch protection strategy → **Require all 9 status checks** (blocking with override)
7. ✅ Matrix testing strategy → **Python 3.12, 3.13** (parallel)

### Phase 1: Design & Contracts ✅ COMPLETE

**Status**: COMPLETE
**Outputs**:
- `data-model.md` - Conceptual entities and data flow
- `contracts/ci-workflow.yml` - Main CI/CD pipeline specification
- `contracts/security-workflow.yml` - Security scanning specification
- `quickstart.md` - Implementation guide
- `CLAUDE.md` - Updated agent context

**Design Decisions**:
- **No persistent storage** - All data managed by GitHub Actions and Codecov
- **Conceptual entities** - Check Run, Check Suite, Annotation, Coverage Report, Security Vulnerability, Merge Status, Workflow Run, Retry Context
- **Workflow structure** - 2 parallel workflows (CI + Security) with 9 total checks
- **Retry patterns** - Consistent 3-retry strategy for tests and external services
- **SARIF integration** - All security findings uploaded to GitHub Security tab

### Phase 2: Task Generation (Next Step)

**Command**: `/speckit.tasks`

**Expected Output**: `tasks.md` with dependency-ordered implementation tasks

**Estimated Tasks**: 15-20 tasks covering:
- Workflow file creation (2 tasks)
- Configuration file updates (3-4 tasks)
- Dependency installation (2 tasks)
- Branch protection setup (1 task)
- Testing and validation (5-7 tasks)
- Documentation updates (2-3 tasks)

---

## Constitution Check (Post-Design)

**Status**: ✅ PASSED (re-verified after Phase 1)

**Findings**: No constitution violations. Design adds infrastructure configuration only, no application code. All clarifications resolved, all NEEDS CLARIFICATION items addressed through research phase.

**Readiness**: ✅ Ready to proceed to `/speckit.tasks` for task generation.
