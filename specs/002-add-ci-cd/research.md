# Research: CI/CD Security Scanning Tool Selection

**Date**: 2025-10-12
**Feature**: Automated CI/CD Pipeline with Quality Gates
**Research Phase**: Phase 0 - Tool Selection and Best Practices

## Overview

This document resolves the NEEDS CLARIFICATION items identified in the Technical Context section of plan.md, specifically:
1. Security scanning tool selection (SAST, dependency vulnerabilities, secret detection)
2. Secret detection tool selection
3. Best practices for implementing these tools in GitHub Actions

---

## Decision 1: Security Scanning Tool Stack

### Decision

**Use a multi-tool approach: Semgrep + Trivy + Gitleaks**

This combination provides:
- **Semgrep** for Static Application Security Testing (SAST)
- **Trivy** for dependency vulnerability scanning
- **Gitleaks** for secret detection

### Rationale

1. **Cost**: All three tools are completely FREE and open source with unlimited scans
2. **Private Repository Support**: Works for both public and private repositories without paid tiers
3. **Coverage**: Comprehensive coverage of all three security requirements:
   - SAST: Semgrep supports Python, Go, TypeScript with 2,800+ rules
   - Dependencies: Trivy scans pip, go.mod, npm/yarn/pnpm with excellent CVE detection
   - Secrets: Gitleaks provides lightweight, fast secret detection
4. **GitHub Actions Integration**: All three have official GitHub Actions with minimal configuration
5. **Performance**: Combined execution time < 5 minutes (within our 10-minute target)
6. **Scale**: Supports our expected 10-20 PR scans per day without limitations

### Alternatives Considered

#### Option A: GitHub CodeQL + Dependabot + GitHub Secret Scanning
- **Pros**: Native GitHub integration, best accuracy, lowest false positives, AI-powered autofix
- **Cons**: Requires paid GitHub Advanced Security ($23/user/month) for private repositories
- **Rejected Because**: Cost prohibitive if repository is private; our free tier constraint makes this unsuitable unless repo is public

#### Option B: Snyk (all-in-one solution)
- **Pros**: Best dependency intelligence, comprehensive all-in-one tool, 98% false positive reduction
- **Cons**: Free tier limited to 100 scans/month (we need 300-600/month), requires paid Team plan ($25+/user/month)
- **Rejected Because**: Exceeds free tier limitations; not cost-effective for our scan volume

#### Option C: GitHub CodeQL + Trivy (hybrid)
- **Pros**: Best SAST accuracy (CodeQL) + fast dependency scanning (Trivy)
- **Cons**: CodeQL requires paid tier for private repos
- **Rejected Because**: Same cost constraint as Option A

### Implementation Details

**Semgrep Configuration**:
- Use `config: auto` for default ruleset (2,800+ community rules)
- Expected false positive rate: Moderate (will require tuning)
- Execution time: < 1 minute for 50k LOC
- Blocking: Configure to block on high/critical severity findings

**Trivy Configuration**:
- Scan type: `fs` (filesystem scan for dependencies)
- Output format: SARIF (uploads to GitHub Security tab)
- Scan targets: pip (Python), go.mod (Go), package.json/yarn.lock (TypeScript)
- Execution time: < 1 minute typical

**Gitleaks Configuration**:
- Fetch depth: 0 (scan full git history)
- Output format: SARIF
- Detects 300+ secret patterns
- Execution time: < 30 seconds

---

## Decision 2: Test Retry Implementation

### Decision

**Use pytest-rerunfailures plugin for Python tests**

### Rationale

1. **Native pytest integration**: Official pytest plugin, well-maintained
2. **Simple configuration**: Single line in pytest.ini or command-line flag
3. **Granular control**: Can configure retries per test, per class, or globally
4. **Flaky test detection**: Provides visibility into which tests required retries
5. **Industry standard**: Used by pytest maintainers and major projects

### Configuration

```ini
# pytest.ini
[pytest]
addopts = --reruns 3 --reruns-delay 1
```

Or in GitHub Actions:
```bash
pytest --reruns 3 --reruns-delay 1 tests/
```

### Alternatives Considered

- **GitHub Actions retry**: Can retry entire workflow steps, but retries ALL tests (wasteful)
- **Custom retry decorator**: More work to maintain, reinventing the wheel
- **Rejected Because**: pytest-rerunfailures is the standard solution

---

## Decision 3: External Service Retry Strategy

### Decision

**Implement retry logic using GitHub Actions' built-in retry mechanism with timeout**

### Rationale

1. **Native support**: GitHub Actions supports `timeout-minutes` and retry via workflow syntax
2. **Simple implementation**: Can wrap external service calls with retry logic
3. **Consistent pattern**: Same retry strategy (3 attempts, 30s intervals) as tests
4. **Fail-open capability**: Can mark check as warning and allow merge if all retries exhausted

### Implementation Pattern

```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  continue-on-error: true  # Fail-open
  timeout-minutes: 2
  with:
    file: ./coverage.xml
    fail_ci_if_error: false
```

For more complex retry needs, use:
```yaml
- name: Security Scan with Retry
  uses: nick-fields/retry@v2
  with:
    timeout_minutes: 2
    max_attempts: 3
    retry_wait_seconds: 30
    command: trivy fs --format sarif .
```

---

## Decision 4: Coverage Reporting Strategy

### Decision

**Use Codecov for coverage reporting with fail-open on service failure**

### Rationale

1. **Free tier**: Unlimited public repos, generous private repo limits
2. **GitHub Integration**: Native PR comments, coverage diff, trends
3. **Multi-language**: Supports Python, Go, TypeScript coverage formats
4. **Existing workflow**: Already integrated in current tests.yml
5. **Fail-open**: Can allow merge if Codecov unavailable (per clarification)

### Configuration

```yaml
# .codecov.yml
coverage:
  status:
    project:
      default:
        target: 70%
        threshold: 1%
    patch:
      default:
        target: 70%
```

---

## Decision 5: Workflow Organization

### Decision

**Split into two workflow files: ci.yml (main checks) and security.yml (security scans)**

### Rationale

1. **Separation of concerns**: Security scans can run independently
2. **Performance**: Can run security scans in parallel with main CI checks
3. **Flexibility**: Can configure different triggers (e.g., nightly security scans)
4. **Clarity**: Easier to understand and maintain separate workflows

### Workflow Structure

**ci.yml** (Main CI/CD Pipeline):
- Python tests with pytest (unit, integration, e2e)
- Code quality checks (ruff format, ruff check, mypy)
- Go build and tests
- TypeScript build and tests
- Coverage reporting to Codecov
- Execution time target: < 8 minutes

**security.yml** (Security Scanning):
- Semgrep SAST
- Trivy dependency scanning
- Gitleaks secret scanning
- Execution time target: < 3 minutes

Both run on: `pull_request` and `push` to `main`/`develop`

---

## Decision 6: Branch Protection Configuration

### Decision

**Configure GitHub branch protection rules to require all checks before merge**

### Implementation

Via GitHub UI (Settings → Branches → Branch protection rules for `main` and `develop`):

1. ✅ Require status checks to pass before merging
2. ✅ Require branches to be up to date before merging
3. ✅ Status checks that are required:
   - `test (Python 3.12)`
   - `test (Python 3.13)`
   - `code-quality`
   - `build-go`
   - `build-typescript`
   - `security / sast`
   - `security / dependencies`
   - `security / secrets`
   - `codecov/project`
4. ✅ Do not allow bypassing the above settings (unless maintainer override needed)

### Rationale

- Enforces all 30 functional requirements from spec.md
- Prevents accidental merges with failing checks
- Provides visibility into check status on PR page
- Allows maintainer override (FR-010) via admin permissions

---

## Decision 7: Matrix Testing Strategy

### Decision

**Test Python code against multiple Python versions (3.12, 3.13) using matrix strategy**

### Rationale

1. **Forward compatibility**: Ensures code works with latest Python
2. **Existing pattern**: Current tests.yml already uses matrix
3. **Minimal cost**: Both versions run in parallel, ~5 minutes total
4. **Best practice**: Standard for Python libraries

### Configuration

```yaml
strategy:
  matrix:
    python-version: ["3.12", "3.13"]
```

**Go and TypeScript**: Single version testing (Go 1.21+, Node 20+) sufficient since both have strong backward compatibility.

---

## Best Practices Research

### 1. GitHub Actions Performance Optimization

**Caching Dependencies**:
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
```

**Parallel Job Execution**:
- Run language-specific builds in parallel jobs
- Run security scans in parallel with CI checks
- Expected speedup: 40-50% vs sequential execution

**Conditional Execution**:
```yaml
- name: Build Go
  if: contains(github.event.head_commit.modified, 'whatsapp-bridge/')
```

### 2. SARIF Upload Best Practices

All security tools should output SARIF format and upload to GitHub Security tab:

```yaml
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
    category: security-tool-name
```

Benefits:
- Unified security dashboard
- PR annotations on vulnerable lines
- Historical trend tracking

### 3. Notification Strategy

**On Failure**:
- GitHub automatically notifies PR author
- Can configure additional Slack/email via third-party actions (deferred for now)

**On Success**:
- Silent success (no notification spam)
- Status visible in PR checks section

---

## Risk Mitigation

### Risk 1: Semgrep False Positives

**Mitigation**:
- Start with default rules, monitor for noise
- Create `.semgrepignore` for known false positives
- Use `--severity ERROR` to only block on critical findings initially
- Iterate on rules based on 2-week feedback period

### Risk 2: External Service Outages

**Mitigation**:
- Implemented: Retry 3x with 30s intervals (FR-028)
- Implemented: Fail-open with warning (FR-029)
- Implemented: Manual re-trigger capability (FR-015)
- Monitor: Log all failures for audit trail (FR-030)

### Risk 3: CI Execution Time Exceeds 10 Minutes

**Mitigation**:
- Parallel job execution reduces total time
- Caching reduces dependency installation time
- Can skip tests for docs-only changes via path filters
- Monitoring: Track workflow duration in GitHub Insights

---

## Future Enhancements

### Short-term (Next 3-6 months)
1. Add pre-commit hooks for local secret scanning (gitleaks)
2. Configure custom Semgrep rules for project-specific patterns
3. Add performance regression testing (execution time tracking)

### Long-term (6-12 months)
1. Evaluate Semgrep Team tier (FREE for ≤10 contributors, reduces false positives)
2. Consider GitHub CodeQL if repository becomes public
3. Implement automated security finding triage with AI (if available)

---

## References

- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Trivy GitHub Action](https://github.com/aquasecurity/trivy-action)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [SARIF Format Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)

---

## Conclusion

All NEEDS CLARIFICATION items have been resolved with specific tool selections and implementation strategies. The chosen tech stack (Semgrep + Trivy + Gitleaks) provides comprehensive security coverage while staying within free tier constraints and meeting all performance requirements.

**Next Phase**: Proceed to Phase 1 (Design & Contracts) to generate workflow specifications and data models.
