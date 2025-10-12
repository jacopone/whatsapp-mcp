# Quickstart Guide: CI/CD Pipeline Implementation

**Feature**: Automated CI/CD Pipeline with Quality Gates
**Branch**: `002-add-ci-cd`
**Target Audience**: Developers implementing this feature

## Overview

This guide walks through implementing the automated CI/CD pipeline with quality gates for the WhatsApp MCP server project. After completion, all pull requests will automatically run tests, code quality checks, security scans, and build verification before allowing merge.

**Estimated implementation time**: 4-6 hours

---

## Prerequisites

- [x] Repository access with ability to create workflows
- [x] GitHub repository (public or private)
- [x] Existing test suite (101 tests currently passing)
- [x] Python 3.12+, Go 1.21+, Node.js 20+ installed locally for testing

---

## Implementation Steps

### Step 1: Install pytest-rerunfailures (5 minutes)

**Purpose**: Enable automatic retry for flaky tests (FR-025, FR-027)

1. Add to `unified-mcp/pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   dev = [
       "pytest>=7.0.0",
       "pytest-cov>=4.0.0",
       "pytest-rerunfailures>=12.0",  # NEW
       "ruff>=0.1.0",
       "mypy>=1.0.0",
   ]
   ```

2. Test locally:
   ```bash
   cd unified-mcp
   pip install -e ".[dev]"
   pytest tests/ --reruns 3 --reruns-delay 1 -v
   ```

3. Verify flaky test detection works (if any tests are flaky, you'll see warnings)

---

### Step 2: Create CI Workflow (30 minutes)

**Purpose**: Implement main CI/CD pipeline (FR-001 through FR-020)

1. Create `.github/workflows/ci.yml`:
   ```bash
   mkdir -p .github/workflows
   ```

2. Copy the workflow specification from `specs/002-add-ci-cd/contracts/ci-workflow.yml` to `.github/workflows/ci.yml`

3. Customize if needed:
   - Adjust Python versions in matrix (currently 3.12, 3.13)
   - Adjust working directories if your structure differs
   - Modify coverage threshold if not using 70%

4. **Test locally before committing**:
   ```bash
   # Install act (GitHub Actions local runner)
   # https://github.com/nektos/act

   # Test the workflow
   act pull_request -W .github/workflows/ci.yml
   ```

5. Commit and push:
   ```bash
   git add .github/workflows/ci.yml unified-mcp/pyproject.toml
   git commit -m "feat: add CI workflow with test retry and coverage checks"
   git push
   ```

---

### Step 3: Create Security Workflow (30 minutes)

**Purpose**: Implement security scanning (FR-021 through FR-024)

1. Create `.github/workflows/security.yml`:
   - Copy from `specs/002-add-ci-cd/contracts/security-workflow.yml` to `.github/workflows/security.yml`

2. **No secrets required** for basic setup:
   - Semgrep, Trivy, Gitleaks all work without authentication
   - Optional: Add `SEMGREP_APP_TOKEN` for advanced features later

3. Commit and push:
   ```bash
   git add .github/workflows/security.yml
   git commit -m "feat: add security scanning workflow (SAST, dependencies, secrets)"
   git push
   ```

---

### Step 4: Configure Codecov (15 minutes)

**Purpose**: Enable test coverage reporting and tracking (FR-007, FR-008)

1. Sign up at https://codecov.io (free for public repos)

2. Add repository to Codecov

3. Create `.codecov.yml` in repository root:
   ```yaml
   coverage:
     status:
       project:
         default:
           target: 70%
           threshold: 1%
       patch:
         default:
           target: 70%

   comment:
     layout: "reach, diff, flags, files"
     behavior: default

   ignore:
     - "tests/**"
     - "**/__pycache__/**"
   ```

4. Add `CODECOV_TOKEN` to GitHub secrets (private repos only):
   - Go to repository Settings → Secrets and variables → Actions
   - Add new secret: `CODECOV_TOKEN` = `<token from Codecov dashboard>`

5. Commit:
   ```bash
   git add .codecov.yml
   git commit -m "feat: add Codecov configuration for 70% coverage threshold"
   git push
   ```

---

### Step 5: Configure Branch Protection (15 minutes)

**Purpose**: Enforce quality gates and prevent merges with failing checks (FR-009, FR-010)

1. Go to repository Settings → Branches

2. Add branch protection rule for `main`:
   - Branch name pattern: `main`
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - Select required status checks:
     - `test (Python 3.12)`
     - `test (Python 3.13)`
     - `code-quality`
     - `build-go`
     - `build-typescript`
     - `sast`
     - `dependencies`
     - `secrets`
     - `codecov/project`

3. Optional settings:
   - ✅ Require conversation resolution before merging
   - ✅ Do not allow bypassing the above settings (removes maintainer override)
   - ❌ Allow force pushes (recommended: disabled)

4. Repeat for `develop` branch if used

5. Save changes

---

### Step 6: Test the Pipeline (30 minutes)

**Purpose**: Verify all checks work as expected

1. Create a test pull request:
   ```bash
   git checkout -b test-ci-pipeline
   echo "# Test PR" > TEST.md
   git add TEST.md
   git commit -m "test: verify CI pipeline"
   git push -u origin test-ci-pipeline
   ```

2. Open PR on GitHub

3. Verify all checks run:
   - Wait for checks to start (should be < 2 minutes per FR-012)
   - All 9 checks should appear:
     - 2× test (Python 3.12, 3.13)
     - 1× code-quality
     - 1× build-go
     - 1× build-typescript
     - 1× sast (Semgrep)
     - 1× dependencies (Trivy)
     - 1× secrets (Gitleaks)
     - 1× codecov/project
   - Total execution time should be < 10 minutes

4. Check for issues:
   - ❌ Any red X? Click "Details" to see logs
   - ⚠️ Coverage below 70%? Add tests or adjust threshold
   - 🔴 Security findings? Review and fix or mark false positive

5. Once all green:
   - Merge status should show "Ready to merge"
   - Close the test PR (don't merge)

---

### Step 7: Test Flaky Test Detection (Optional, 15 minutes)

**Purpose**: Verify retry logic works (FR-025, FR-026, FR-027)

1. Create a temporarily flaky test:
   ```python
   # unified-mcp/tests/unit/test_flaky.py
   import random
   import pytest

   def test_flaky_example():
       """This test fails 50% of the time to demonstrate retry behavior"""
       if random.random() < 0.5:
           pytest.fail("Simulated flaky failure")
   ```

2. Push and create PR:
   ```bash
   git add unified-mcp/tests/unit/test_flaky.py
   git commit -m "test: add flaky test to verify retry logic"
   git push
   ```

3. Observe behavior:
   - Test will fail initially
   - pytest-rerunfailures will retry up to 3 times
   - If any retry succeeds, test passes with "RERUN" annotation
   - Check run output will show "1 rerun" in summary

4. Remove flaky test after verification:
   ```bash
   git rm unified-mcp/tests/unit/test_flaky.py
   git commit -m "test: remove flaky test example"
   git push
   ```

---

### Step 8: Test External Service Failure (Optional, 15 minutes)

**Purpose**: Verify fail-open behavior when Codecov unavailable (FR-028, FR-029, FR-030)

1. Temporarily disable Codecov token:
   - Go to repository Settings → Secrets → Actions
   - Remove or rename `CODECOV_TOKEN`

2. Create PR and observe:
   - codecov/project check will show "neutral" (yellow)
   - PR can still merge (fail-open behavior)
   - Check logs show retry attempts with 30s intervals

3. Restore Codecov token after testing

---

## Verification Checklist

After completing all steps, verify:

- [ ] All workflows appear in Actions tab
- [ ] Test PR triggered all 9 checks within 2 minutes
- [ ] All checks completed within 10 minutes
- [ ] Coverage report appears on PR as comment
- [ ] Security findings (if any) appear in Security tab
- [ ] Branch protection prevents merge when checks fail
- [ ] PR shows "Ready to merge" only when all checks pass
- [ ] Test retry logic works (if you have flaky tests)
- [ ] Fail-open works for external service failures

---

## Troubleshooting

### Issue: Workflows not triggering

**Symptoms**: PR created but no checks appear

**Solutions**:
1. Check workflow files are in `.github/workflows/` directory
2. Verify YAML syntax: `yamllint .github/workflows/*.yml`
3. Check workflow triggers match your branch names
4. Ensure PR is not marked as draft (workflows skip drafts per FR-019)

### Issue: Tests failing in CI but passing locally

**Symptoms**: Tests pass on local machine but fail in GitHub Actions

**Solutions**:
1. Check Python version matches (CI uses 3.12, 3.13)
2. Verify dependencies are pinned in pyproject.toml
3. Check for environment-specific issues (paths, timezone, etc.)
4. Run tests with same pytest flags as CI: `pytest --reruns 3 -v`

### Issue: Security scan false positives

**Symptoms**: Semgrep/Trivy reporting issues that are not real vulnerabilities

**Solutions**:
1. Review finding details in Security tab
2. For false positives:
   - Semgrep: Add to `.semgrepignore` or use inline `# nosemgrep` comment
   - Trivy: Add to `.trivyignore` with justification
3. For Gitleaks: Add to `.gitleaks.toml` allowlist with reason

### Issue: Coverage failing below 70%

**Symptoms**: codecov/project check failing with "Coverage not met"

**Solutions**:
1. Add tests for uncovered code (preferred)
2. Review Codecov PR comment to see which lines are uncovered
3. Temporary: Lower threshold in `.codecov.yml` (not recommended)
4. Use `# pragma: no cover` for truly untestable code (use sparingly)

### Issue: Workflows taking too long

**Symptoms**: Checks taking > 10 minutes to complete

**Solutions**:
1. Check for network timeouts in logs
2. Add dependency caching (already in workflow, verify it's working)
3. Consider splitting large test files
4. Run security scans less frequently (e.g., nightly only)

---

## Configuration Files Reference

### pytest.ini (optional)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    -ra
    --reruns 3
    --reruns-delay 1
markers =
    integration: Integration tests
    e2e: End-to-end tests
    unit: Unit tests
```

### .semgrepignore (optional)
```
# Ignore test files from security scanning
tests/
*_test.py
test_*.py

# Ignore generated files
**/__pycache__/
*.pyc
```

### .trivyignore (optional)
```
# Example: Ignore known false positive
# CVE-2024-12345
# Reason: Not applicable to our use case because [explanation]
```

---

## Performance Benchmarks

Expected workflow execution times (based on research):

| Check | Expected Duration | Timeout |
|-------|------------------|---------|
| test (Python 3.12) | 2-3 minutes | 10 min |
| test (Python 3.13) | 2-3 minutes | 10 min |
| code-quality | 30-60 seconds | 5 min |
| build-go | 1-2 minutes | 5 min |
| build-typescript | 1-2 minutes | 5 min |
| sast (Semgrep) | 30-60 seconds | 5 min |
| dependencies (Trivy) | 30-60 seconds | 5 min |
| secrets (Gitleaks) | 10-30 seconds | 2 min |
| codecov upload | 10-30 seconds | 2 min |
| **Total (parallel)** | **5-8 minutes** | **15 min** |

---

## Success Criteria

This implementation is complete when:

✅ **SC-001**: 100% of PRs trigger checks within 2 minutes
✅ **SC-002**: 95% of PRs get results within 10 minutes
✅ **SC-003**: Zero PRs with failing tests merged without override
✅ **SC-004**: Coverage stays at or above 70%
✅ **SC-005**: Code quality issues detected in 100% of PRs with issues
✅ **SC-006**: Build breakages detected in 100% of cases
✅ **SC-011**: Security vulnerabilities detected in 100% of PRs with issues

---

## Next Steps

After completing this quickstart:

1. **Monitor for 2 weeks**:
   - Track workflow execution times in GitHub Insights
   - Monitor false positive rate from security scans
   - Collect developer feedback on check reliability

2. **Tune security scans**:
   - Add project-specific Semgrep rules
   - Configure ignores for known false positives
   - Adjust severity thresholds if needed

3. **Optimize performance**:
   - Add more aggressive caching if needed
   - Consider conditional workflow execution (e.g., only run Go checks if Go files changed)

4. **Consider enhancements**:
   - Add pre-commit hooks for local checks
   - Set up Slack notifications for failed checks
   - Implement custom GitHub Actions for project-specific validation

---

## Support

**Questions or issues?**
- Check workflow logs: GitHub Actions tab → Select failed run → Click job → View logs
- Review specification: `specs/002-add-ci-cd/spec.md`
- Review research: `specs/002-add-ci-cd/research.md`
- Review contracts: `specs/002-add-ci-cd/contracts/`

**Common resources**:
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest-rerunfailures Documentation](https://github.com/pytest-dev/pytest-rerunfailures)
- [Semgrep Rules](https://semgrep.dev/explore)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Codecov Documentation](https://docs.codecov.com/)

---

**Implementation Date**: 2025-10-12
**Specification Version**: 1.0
**Branch**: 002-add-ci-cd
