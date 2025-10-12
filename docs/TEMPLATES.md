# Documentation Templates

See full templates in:
- API Tool Template: `specs/004-update-readme-and/contracts/api-tool-template.md`
- Troubleshooting Template: `specs/004-update-readme-and/contracts/troubleshooting-template.md`

## Quick API Tool Format

```markdown
### tool_name

**Category**: [Category] | **Backend**: [Go Bridge/Baileys Bridge/Hybrid]

[Purpose description]

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| param | type | Yes/No | value | description |

**Returns**: [Return structure]

**Example**:
\`\`\`python
# Example code
\`\`\`

**Error Codes**: ERROR_CODE - description
```

## Quick Troubleshooting Format

```markdown
## Issue Title

**Symptoms**: What user sees
**Diagnosis**: Root cause
**Solution**: Step-by-step fix
**Verification**: How to confirm fix worked
```
