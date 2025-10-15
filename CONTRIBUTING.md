# Contributing to WhatsApp MCP Documentation

Thank you for your interest in improving the WhatsApp MCP documentation! This guide will help you contribute effectively.

---

## Documentation Structure

Our documentation is organized into several categories:

```
whatsapp-mcp/
├── README.md                    # Main entry point, architecture overview
├── API_REFERENCE.md             # Complete tool reference (75 tools)
├── TROUBLESHOOTING.md           # Common issues and solutions (24 issues)
├── docs/
│   ├── examples/                # Practical usage examples
│   │   ├── basic-messaging.md
│   │   ├── community-management.md
│   │   └── hybrid-operations.md
│   ├── BACKEND_ROUTING.md       # Routing decision tree
│   ├── COMMON_PATTERNS.md       # Usage patterns
│   ├── ERROR_HANDLING.md        # Error codes and handling
│   └── STYLE_GUIDE.md           # Documentation style conventions
└── CONTRIBUTING.md              # This file
```

---

## What to Contribute

We welcome contributions in these areas:

### 1. New Usage Examples
- Create examples for common workflows
- Add examples to `docs/examples/`
- Follow the 10-example structure pattern

### 2. API Documentation Updates
- Document new tools in `API_REFERENCE.md`
- Update tool parameters, return values, or examples
- Add new error codes with resolution steps

### 3. Troubleshooting Issues
- Add common issues to `TROUBLESHOOTING.md`
- Include: Symptoms, Diagnosis, Solution, Verification
- Organize by severity (Critical, High, Medium, Low)

### 4. Common Patterns
- Add multi-tool workflows to `COMMON_PATTERNS.md`
- Include working Python code examples
- Show practical use cases

### 5. Error Handling
- Document new error codes in `ERROR_HANDLING.md`
- Add error handling patterns
- Provide debugging tips

---

## Documentation Style Guide

### Formatting

**Use consistent formatting** throughout:
- Headers: ATX-style (`# Header`, `## Subheader`)
- Code blocks: Always specify language (```python, ```bash, ```json)
- Lists: Use `-` for unordered, `1.` for ordered
- Emphasis: `**bold**` for important, `*italic*` for technical terms

### Code Examples

**All code examples must be**:
1. **Working** - Tested and functional
2. **Complete** - Include imports, setup, error handling
3. **Commented** - Explain non-obvious logic
4. **Copy-paste ready** - Users should be able to run them directly

**Example structure**:
```python
# Step 1: Import required functions
from whatsapp import send_text_message_v2, check_is_on_whatsapp

# Step 2: Verify contact exists
check = check_is_on_whatsapp(phone="+1234567890")

if check["is_on_whatsapp"]:
    # Step 3: Send message
    result = send_text_message_v2(
        chat_jid=check["jid"],
        text="Hello from WhatsApp MCP!"
    )

    # Step 4: Verify delivery
    if result["success"]:
        print(f"✅ Message sent to {check['jid']}")
else:
    print(f"❌ {check['phone']} is not on WhatsApp")
```

### Technical Writing

**Be clear and precise**:
- Use active voice ("The bridge connects" not "Connection is made")
- Be specific ("Wait 5 seconds" not "Wait briefly")
- Avoid jargon or explain it when necessary
- Write for developers of all skill levels

**Example - Poor**:
> "The system might experience issues if bridges aren't properly configured."

**Example - Good**:
> "If both bridges are not running on ports 8080 (Go) and 8081 (Baileys), MCP tools will return `BRIDGE_UNREACHABLE` errors."

### Error Documentation

**When documenting errors**, include:
1. **Error Code**: Machine-readable identifier (e.g., `BRIDGE_UNREACHABLE`)
2. **Description**: What the error means
3. **Resolution**: Step-by-step fix
4. **Verification**: How to confirm fix worked

**Template**:
```markdown
### ERROR_CODE_NAME

**Description**: Brief explanation of what this error means.

**Causes**:
- Cause 1
- Cause 2

**Resolution**:
```bash
# Step 1: Diagnostic command
command-to-diagnose

# Step 2: Fix command
command-to-fix
```

**Verification**:
```bash
# Command to verify fix
verification-command
# Expected output: "Success message"
```
```

---

## Tool Documentation Template

When documenting a new MCP tool in `API_REFERENCE.md`, follow this template:

```markdown
### tool_name

**Category**: Category Name | **Backend**: Go/Baileys/Hybrid

Brief description of what this tool does (1-2 sentences).

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| param1 | string | Yes | - | Description of param1 |
| param2 | integer | No | 0 | Description of param2 |

**Returns**:

```json
{
  "success": true,
  "field1": "value",
  "field2": 123
}
```

**Example**:

```python
# Import the tool
from whatsapp import tool_name

# Use the tool
result = tool_name(param1="value", param2=123)

if result["success"]:
    print(f"✅ Success: {result['field1']}")
else:
    print(f"❌ Failed: {result['message']}")
```

**Error Codes**:

| Error Code | Description | Resolution |
|------------|-------------|------------|
| ERROR_1 | Brief description | How to fix |
| ERROR_2 | Brief description | How to fix |

**Related Tools**:
- `related_tool_1()` - Brief explanation
- `related_tool_2()` - Brief explanation
```

---

## Contribution Workflow

### 1. Before You Start

**Check existing documentation**:
- Review [API_REFERENCE.md](./API_REFERENCE.md) for tool docs
- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for similar issues
- Look at [docs/examples/](./docs/examples/) for example patterns

**Avoid duplicates**: Search existing docs before adding new content.

### 2. Making Changes

**Local setup**:
```bash
# Fork the repository on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/whatsapp-mcp.git
cd whatsapp-mcp

# Add upstream remote (original repository)
git remote add upstream https://github.com/lharries/whatsapp-mcp.git

# Fetch upstream changes
git fetch upstream

# Create feature branch from develop (for active development)
git checkout develop
git checkout -b feature/your-improvement-name

# Make your changes
# Edit the relevant markdown files
```

**Git Workflow** (for forks):

We use a three-branch workflow for organized development:

```
feature branches → develop (integration) → main (PR-ready) → upstream PR
```

- **`develop`** - Active integration branch where all feature work is merged
- **`main`** - Clean, PR-ready branch that tracks upstream/main
- **`feature/*`** - Feature branches created from develop

**Workflow steps**:

```bash
# 1. Work on your feature branch
git checkout -b feature/your-feature develop
# ... make changes ...
git add .
git commit -m "feat: your feature description"

# 2. Merge into develop (integration testing)
git checkout develop
git merge feature/your-feature
git push origin develop

# 3. When ready for PR to upstream, merge develop into main
git checkout main
git merge develop
git push origin main

# 4. Create PR from your fork's main to upstream/main
# (Use GitHub web interface to create PR)

# 5. Clean up feature branches after merging
git branch -d feature/your-feature
git push origin --delete feature/your-feature
```

**Why this workflow?**
- Keep `develop` as active workspace with all WIP features
- Keep `main` clean and synced with upstream (easier to merge PRs)
- Test feature integration in `develop` before promoting to `main`
- Easy to stay up-to-date with upstream changes

**Preview changes**:
```bash
# Use a markdown previewer (e.g., glow)
glow README.md

# Or open in your editor with markdown preview
code README.md
```

### 3. Quality Checks

**Before submitting**, verify:
- ✅ All code examples are tested and working
- ✅ Links are valid and point to correct locations
- ✅ Markdown formatting is consistent
- ✅ No spelling or grammar errors
- ✅ Cross-references are accurate

**Check links**:
```bash
# Find broken links (manual check)
grep -r "](.*\.md)" *.md docs/*.md
```

### 4. Submitting

**Create pull request** (following the three-branch workflow):
```bash
# Stage and commit your changes on feature branch
git add .
git commit -m "docs: improve [section name] documentation"

# Push feature branch to your fork
git push origin feature/your-improvement-name

# Merge into develop for integration
git checkout develop
git merge feature/your-improvement-name
git push origin develop

# When ready for upstream PR, merge develop into main
git checkout main
git merge develop
git push origin main

# Create PR on GitHub: your-fork/main → lharries/main
```

**Alternative** (for quick documentation fixes):
```bash
# For small doc fixes, you can work directly on main
git checkout main
git add .
git commit -m "docs: fix typo in API reference"
git push origin main

# Then create PR: your-fork/main → lharries/main
```

**PR description should include**:
- What documentation was added/changed
- Why the change improves the docs
- Any related issues

**PR template**:
```markdown
## Documentation Improvement

**Type**: [New Example / Tool Update / Troubleshooting / Pattern / Other]

**Changes**:
- Added [description]
- Updated [description]
- Fixed [description]

**Testing**:
- [ ] All code examples tested
- [ ] Links verified
- [ ] Formatting checked
- [ ] Spell check passed

**Branch**: Merged from develop (or main for quick fixes)

**Related Issues**: #123 (if applicable)
```

---

## Documentation Conventions

### Backend Badges

Always indicate which backend handles a tool:

- **Backend: Go** - Go bridge (port 8080)
- **Backend: Baileys** - Baileys bridge (port 8081)
- **Backend: Hybrid** - Combines both bridges

### Category Labels

Use consistent category names:
- Messaging
- Contacts
- Chats
- Communities
- History Sync
- Message Query
- Privacy
- Business
- Newsletters
- Backend Status

### Example Numbering

**For example files**, use:
- **Example 1**: First workflow
- **Example 2**: Second workflow
- **Example 10**: Tenth workflow

Number consecutively from 1.

### Severity Levels

**For troubleshooting issues**, use:
- 🔴 **Critical** - Blocks setup or core functionality
- 🟠 **High** - Major feature broken but workarounds exist
- 🟡 **Medium** - Minor feature issue or performance degradation
- 🟢 **Low** - Cosmetic or edge case issues

---

## Code of Conduct

**Be respectful**:
- Welcome newcomers
- Provide constructive feedback
- Assume good intentions
- Focus on improving documentation quality

**Documentation quality standards**:
- Accuracy over brevity
- Clarity over cleverness
- Practical over theoretical
- Tested over assumed

---

## Getting Help

**Questions about contributing?**
1. Check existing examples in `docs/examples/`
2. Review the [Style Guide](./docs/STYLE_GUIDE.md)
3. Open a GitHub Discussion for questions
4. Tag maintainers in your PR for review

**Common questions**:

**Q: Where should I add a new usage example?**
A: Add to existing example files (`docs/examples/*.md`) or create a new file if it's a distinct category.

**Q: How do I test MCP tools for documentation?**
A: Follow the [Quick Start](#quick-start) in README.md to set up both bridges, then test your examples in Claude Desktop or Cursor.

**Q: Should I update multiple files for a single tool?**
A: Yes! Update `API_REFERENCE.md` (tool docs), add to `COMMON_PATTERNS.md` (if it's a common pattern), and potentially add an example to `docs/examples/`.

---

## Review Process

**Pull requests will be reviewed for**:
1. **Accuracy**: Are the technical details correct?
2. **Completeness**: Are all required sections included?
3. **Clarity**: Is it easy to understand?
4. **Consistency**: Does it match our style guide?
5. **Testing**: Have code examples been verified?

**Review timeline**:
- Initial review: Within 3 days
- Feedback incorporated: Within 1 week
- Final merge: Within 2 weeks

---

## Recognition

**Contributors will be**:
- Listed in documentation credits
- Mentioned in release notes
- Acknowledged in the community

Thank you for helping make WhatsApp MCP documentation better! 🎉
