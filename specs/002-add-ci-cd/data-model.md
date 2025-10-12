# Data Model: CI/CD Pipeline Quality Gates

**Feature**: Automated CI/CD Pipeline with Quality Gates
**Date**: 2025-10-12
**Phase**: Phase 1 - Design & Contracts

## Overview

This feature primarily involves **workflow states and ephemeral data** rather than persistent database entities. All data is managed by GitHub Actions runtime and the GitHub platform. This document describes the conceptual data model for understanding the system's behavior.

---

## Conceptual Entities

### 1. Check Run

Represents a single validation execution (test suite run, linter run, security scan, build attempt).

**Attributes**:
- `id`: string (GitHub-generated unique identifier)
- `name`: string (e.g., "test (Python 3.12)", "security / sast", "code-quality")
- `status`: enum [`queued`, `in_progress`, `completed`]
- `conclusion`: enum [`success`, `failure`, `neutral`, `cancelled`, `timed_out`, `action_required`] (null if not completed)
- `started_at`: timestamp (ISO 8601)
- `completed_at`: timestamp (ISO 8601, null if in progress)
- `duration_seconds`: integer (computed: completed_at - started_at)
- `output_title`: string (summary of check result)
- `output_summary`: text (detailed output, markdown formatted)
- `output_annotations`: array of Annotation (line-level findings, optional)
- `html_url`: URL (link to GitHub Actions run details)
- `retry_count`: integer (number of retries performed, 0-3)
- `is_flaky`: boolean (true if test failed initially but passed on retry)

**Validation Rules**:
- `status` must transition: queued → in_progress → completed
- `conclusion` only set when status = completed
- `duration_seconds` must be >= 0
- `retry_count` must be 0-3 (per FR-025)
- `is_flaky` only true if retry_count > 0 and conclusion = success

**State Transitions**:
```
[queued] → [in_progress] → [completed:success]
                         → [completed:failure]
                         → [completed:neutral]  (external service unavailable)
                         → [completed:cancelled] (PR closed/force-pushed)
                         → [completed:timed_out]
```

**Relationships**:
- Belongs to one Check Suite
- May have many Annotations (for security/linting findings)

---

### 2. Check Suite

Collection of related check runs for a specific commit.

**Attributes**:
- `id`: string (GitHub-generated unique identifier)
- `head_sha`: string (git commit SHA being checked)
- `status`: enum [`queued`, `in_progress`, `completed`]
- `conclusion`: enum [`success`, `failure`, `neutral`, `cancelled`, `timed_out`] (null if not completed)
- `created_at`: timestamp (ISO 8601)
- `updated_at`: timestamp (ISO 8601)
- `check_runs`: array of Check Run
- `pull_request`: reference to Pull Request (if triggered by PR)
- `branch`: string (branch name)
- `workflow_run_id`: string (GitHub Actions workflow run ID)

**Validation Rules**:
- All check_runs must complete before suite conclusion is set
- Suite conclusion = `failure` if ANY check run conclusion = failure (except neutral)
- Suite conclusion = `success` if ALL check runs conclusion = success
- Suite conclusion = `neutral` if ANY check run = neutral AND no failures

**Computed Properties**:
- `total_checks`: count(check_runs)
- `passed_checks`: count(check_runs where conclusion = success)
- `failed_checks`: count(check_runs where conclusion = failure)
- `pending_checks`: count(check_runs where status != completed)
- `aggregate_duration`: sum(check_runs.duration_seconds)

**Relationships**:
- Contains many Check Runs
- Associated with one Pull Request (if PR-triggered)
- Associated with one Workflow Run

---

### 3. Annotation

Line-level finding from security scans, linting, or type checking.

**Attributes**:
- `path`: string (relative file path, e.g., "src/routing.py")
- `start_line`: integer (1-indexed)
- `end_line`: integer (1-indexed, may equal start_line)
- `start_column`: integer (optional, 1-indexed)
- `end_column`: integer (optional, 1-indexed)
- `annotation_level`: enum [`notice`, `warning`, `failure`]
- `message`: string (description of finding)
- `title`: string (short summary, optional)
- `raw_details`: text (full details, markdown formatted, optional)
- `rule_id`: string (e.g., "python.lang.security.audit.sqli", "CWE-89")
- `severity`: enum [`low`, `medium`, `high`, `critical`] (for security findings)

**Validation Rules**:
- `end_line` >= `start_line`
- If `end_line` == `start_line`, then `end_column` >= `start_column` (if columns provided)
- `annotation_level` = `failure` implies blocking check
- Security findings with `severity` = `critical` or `high` should have `annotation_level` = `failure`

**Relationships**:
- Belongs to one Check Run
- May reference a Security Vulnerability (for dependency scans)

---

### 4. Coverage Report

Contains test coverage metrics for the codebase.

**Attributes**:
- `commit_sha`: string (git commit SHA)
- `overall_coverage_percent`: float (0.0-100.0)
- `lines_covered`: integer
- `lines_total`: integer
- `branches_covered`: integer (optional, language-dependent)
- `branches_total`: integer (optional)
- `coverage_delta`: float (-100.0 to +100.0, change from base branch)
- `baseline_coverage_percent`: float (coverage on base branch, e.g., main)
- `meets_threshold`: boolean (true if overall_coverage_percent >= 70%)
- `per_module_coverage`: array of Module Coverage (optional)
- `uncovered_lines`: array of {file: string, lines: array<integer>}
- `report_url`: URL (link to Codecov or coverage HTML)

**Validation Rules**:
- `overall_coverage_percent` = (lines_covered / lines_total) * 100
- `lines_covered` <= `lines_total`
- `branches_covered` <= `branches_total`
- `meets_threshold` = (overall_coverage_percent >= 70.0)
- Per FR-008: Must compare against 70% minimum threshold

**Computed Properties**:
- `coverage_trend`: enum [`improving`, `stable`, `declining`] based on coverage_delta

**Relationships**:
- Associated with one Check Suite
- May have many Module Coverage entries (for multi-module repos)

---

### 5. Module Coverage

Per-module or per-package coverage breakdown.

**Attributes**:
- `module_name`: string (e.g., "routing", "sync", "backends.health")
- `coverage_percent`: float (0.0-100.0)
- `lines_covered`: integer
- `lines_total`: integer
- `file_path`: string (relative path to module root)

**Validation Rules**:
- `coverage_percent` = (lines_covered / lines_total) * 100
- `lines_covered` <= `lines_total`

**Relationships**:
- Belongs to one Coverage Report

---

### 6. Security Vulnerability

Represents a discovered security issue from dependency scanning or SAST.

**Attributes**:
- `id`: string (CVE ID, GHSA ID, or tool-specific ID)
- `type`: enum [`dependency`, `sast`, `secret`]
- `severity`: enum [`low`, `medium`, `high`, `critical`]
- `title`: string (short description)
- `description`: text (detailed vulnerability description)
- `affected_package`: string (for dependency vulns, e.g., "requests==2.28.0")
- `affected_file`: string (for SAST/secrets, relative file path)
- `affected_lines`: array<integer> (for SAST/secrets)
- `cwe_ids`: array<string> (Common Weakness Enumeration IDs, e.g., ["CWE-89"])
- `remediation`: text (fix guidance, markdown formatted)
- `fixed_version`: string (for dependency vulns, recommended upgrade version)
- `references`: array<URL> (links to CVE details, advisories)
- `is_false_positive`: boolean (maintainer-marked, default false)
- `false_positive_justification`: text (required if is_false_positive = true)

**Validation Rules**:
- If `type` = `dependency`, must have `affected_package` and `fixed_version`
- If `type` = `sast` or `secret`, must have `affected_file` and `affected_lines`
- If `is_false_positive` = true, must have `false_positive_justification` (per edge case)
- Per FR-024: `severity` = `critical` or `high` implies blocking check

**Relationships**:
- Associated with one or more Annotations
- May be linked to multiple Check Runs (if found across retries)

---

### 7. Merge Status

Represents the current merge eligibility of a pull request.

**Attributes**:
- `pull_request_number`: integer
- `is_mergeable`: boolean
- `required_checks`: array<string> (list of required check names)
- `passing_checks`: array<string> (check names with conclusion = success)
- `failing_checks`: array<string> (check names with conclusion = failure)
- `pending_checks`: array<string> (check names with status != completed)
- `blocking_reason`: enum [`checks_pending`, `checks_failed`, `none`] (null if mergeable)
- `override_available`: boolean (true if user is maintainer)
- `updated_at`: timestamp (ISO 8601)

**Validation Rules**:
- `is_mergeable` = (passing_checks contains all required_checks AND failing_checks is empty)
- Per FR-009: Merge blocked if any required check fails
- Per FR-010: `override_available` = true only for users with maintainer role
- `blocking_reason` = `checks_pending` if len(pending_checks) > 0
- `blocking_reason` = `checks_failed` if len(failing_checks) > 0
- `blocking_reason` = `none` if is_mergeable = true

**Computed Properties**:
- `completion_percent`: (len(passing_checks) / len(required_checks)) * 100

**Relationships**:
- Associated with one Pull Request
- Derived from one Check Suite

---

### 8. Workflow Run

GitHub Actions workflow execution instance.

**Attributes**:
- `id`: string (GitHub-generated workflow run ID)
- `workflow_name`: string (e.g., "ci.yml", "security.yml")
- `status`: enum [`queued`, `in_progress`, `completed`]
- `conclusion`: enum [`success`, `failure`, `neutral`, `cancelled`, `timed_out`] (null if not completed)
- `triggered_by`: enum [`pull_request`, `push`, `schedule`, `manual`]
- `trigger_event`: string (e.g., "pull_request", "push")
- `ref`: string (branch/tag ref, e.g., "refs/heads/002-add-ci-cd")
- `sha`: string (commit SHA)
- `started_at`: timestamp (ISO 8601)
- `completed_at`: timestamp (ISO 8601, null if in progress)
- `html_url`: URL (link to GitHub Actions run page)
- `runner_name`: string (e.g., "ubuntu-latest")
- `jobs`: array of Job (workflow jobs)

**Validation Rules**:
- Per FR-012: `started_at` must be <= 2 minutes after trigger event
- Per NFR-002: Total duration should be < 10 minutes for 95% of runs
- `status` transitions: queued → in_progress → completed

**Relationships**:
- Contains many Jobs
- Associated with one Check Suite

---

### 9. Retry Context

Tracks retry attempts for failed tests and external service calls.

**Attributes**:
- `entity_type`: enum [`test`, `external_service`]
- `entity_id`: string (test name or service name)
- `attempt_number`: integer (1-4 for tests, 1-4 for services: 1 initial + 3 retries)
- `attempt_status`: enum [`success`, `failure`]
- `attempt_timestamp`: timestamp (ISO 8601)
- `error_message`: text (if failure)
- `duration_seconds`: float

**Validation Rules**:
- `attempt_number` must be 1-4 (per FR-025, FR-028)
- If `entity_type` = `test`, max attempts = 4 (1 initial + 3 retries)
- If `entity_type` = `external_service`, max attempts = 4 with 30-second delays between attempts
- Per FR-027: Entity passes if ANY attempt has `attempt_status` = `success`

**Computed Properties**:
- `is_flaky`: true if first attempt failed but later attempt succeeded
- `total_attempts`: count(attempts)
- `success_on_attempt`: min(attempt_number where attempt_status = success)

**Relationships**:
- Associated with one Check Run

---

## Data Flow Diagrams

### Flow 1: Pull Request Check Execution

```
[Developer pushes to PR]
    ↓
[GitHub triggers webhook] → [Workflow Run created (queued)]
    ↓
[Check Suite created] → status: queued
    ↓
[Workflow Run starts] → status: in_progress (within 2 min per FR-012)
    ↓
[Multiple Check Runs created in parallel]:
    - test (Python 3.12)
    - test (Python 3.13)
    - code-quality
    - security / sast
    - security / dependencies
    - security / secrets
    - build-go
    - build-typescript
    - codecov/project
    ↓
[Each Check Run executes]:
    - status: in_progress
    - Retry logic (if test fails):
        - Retry Context: attempt 1 → failure
        - Retry Context: attempt 2 → success → is_flaky = true
    - Generates Annotations (if findings)
    - Reports Security Vulnerabilities (if found)
    ↓
[Check Run completes] → status: completed, conclusion: success/failure
    ↓
[All Check Runs complete]
    ↓
[Check Suite completes]:
    - Aggregates conclusions
    - conclusion: success if all pass, failure if any fail
    ↓
[Merge Status updated]:
    - is_mergeable = (all required checks passed)
    - blocking_reason = checks_failed if failures exist
    ↓
[PR status updated in GitHub UI]
    ↓
[PR author notified] (per FR-020)
```

### Flow 2: Coverage Report Generation

```
[Test execution completes]
    ↓
[Coverage data collected]: .coverage file generated
    ↓
[Coverage Report created]:
    - overall_coverage_percent calculated
    - coverage_delta computed (vs base branch)
    - meets_threshold = (coverage >= 70%)
    ↓
[Coverage uploaded to Codecov]:
    - Retry logic (if Codecov unavailable):
        - Retry Context: attempt 1 → timeout
        - Retry Context: attempt 2 → timeout
        - Retry Context: attempt 3 → timeout
        - Retry Context: attempt 4 → timeout
        → Mark as neutral, fail-open (per FR-029)
    ↓
[Coverage Check Run updated]:
    - conclusion: success if meets_threshold
    - conclusion: failure if !meets_threshold
    - conclusion: neutral if Codecov unavailable
```

### Flow 3: Security Vulnerability Detection

```
[Security scan executes] (Semgrep, Trivy, Gitleaks)
    ↓
[Vulnerabilities detected]:
    - Security Vulnerability entities created
    - Annotations created (linked to vulnerabilities)
    ↓
[SARIF file generated]:
    - Vulnerabilities serialized to SARIF format
    ↓
[SARIF uploaded to GitHub]:
    - github/codeql-action/upload-sarif
    ↓
[Security tab updated]:
    - Vulnerabilities visible in GitHub Security tab
    - Annotations appear as PR comments
    ↓
[Check Run conclusion determined]:
    - failure if critical/high severity found
    - success if only low/medium or no findings
    ↓
[Merge Status updated]:
    - Blocked if security check failed (per FR-024)
```

---

## Entity Lifecycle

### Check Run Lifecycle

1. **Created** (status: queued)
   - Workflow triggered by PR event
   - Check Run entry created in GitHub API

2. **Started** (status: in_progress)
   - Workflow job begins execution
   - `started_at` timestamp recorded

3. **Retry Logic** (if applicable)
   - If test fails: Retry Context created
   - Up to 3 retry attempts
   - `is_flaky` flag set if later attempt succeeds

4. **Completed** (status: completed)
   - All execution finished
   - `completed_at` timestamp recorded
   - `conclusion` determined (success/failure/neutral)
   - `duration_seconds` computed

5. **Archived**
   - GitHub retains check run data for 90 days (per FR-017)
   - Logs and artifacts preserved

### Security Vulnerability Lifecycle

1. **Detected**
   - Scanner finds issue during check execution
   - Security Vulnerability entity created
   - Annotation created with line-level details

2. **Reported**
   - SARIF uploaded to GitHub Security tab
   - PR comment created (annotation)
   - Check Run marked as failure (if high/critical severity)

3. **Triaged**
   - Developer reviews finding
   - Option 1: Fix vulnerability → new commit → re-scan
   - Option 2: Mark as false positive (per edge case) → `is_false_positive` = true

4. **Resolved**
   - Fix merged OR false positive marked
   - Security Vulnerability marked inactive
   - Check Run passes on next scan

---

## Validation Rules Summary

| Entity | Key Validation | Functional Requirement |
|--------|----------------|------------------------|
| Check Run | Status transitions valid, retry_count ≤ 3 | FR-025, FR-027 |
| Check Suite | Conclusion aggregates all check runs | FR-013 |
| Annotation | Failure-level for high/critical severity | FR-024 |
| Coverage Report | meets_threshold = (coverage >= 70%) | FR-008 |
| Security Vulnerability | Blocking if critical/high severity | FR-024 |
| Merge Status | is_mergeable only if all checks pass | FR-009 |
| Workflow Run | Started within 2 min of trigger | FR-012 |
| Retry Context | Max 4 attempts (1 + 3 retries) | FR-025, FR-028 |

---

## Storage and Persistence

**GitHub Platform Storage**:
- Check Runs, Check Suites: Stored in GitHub API, 90-day retention (FR-017)
- Annotations: Stored with Check Runs, visible in Security tab and PR comments
- Workflow Runs: Stored in GitHub Actions, logs retained per GitHub plan
- Coverage Reports: Stored in Codecov, trends available indefinitely (free tier)
- Security Vulnerabilities: Stored in GitHub Security tab, retained indefinitely

**Ephemeral Data**:
- Retry Context: Only exists during workflow execution, summarized in check output
- Test results: Logged in workflow output, not separately persisted

**No Custom Database Required**: All data managed by GitHub and Codecov platforms.

---

## Conclusion

This CI/CD pipeline feature uses GitHub's native data models (Check Runs, Check Suites, Annotations) with no custom persistent storage. The conceptual entities described here map directly to GitHub API objects and workflow artifacts. All validation rules are enforced through GitHub Actions workflow logic and branch protection settings.

**Next Phase**: Generate API contracts (workflow YAML specifications) in Phase 1 contracts/ directory.
