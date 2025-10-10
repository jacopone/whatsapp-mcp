# End-to-End Integration Tests

This directory contains end-to-end integration tests for the WhatsApp MCP hybrid architecture.

## Prerequisites

Before running tests:

1. **Start Go Bridge** (port 8080):
   ```bash
   cd whatsapp-mcp/whatsapp-bridge
   go build -o whatsapp-bridge *.go
   ./whatsapp-bridge
   ```

2. **Start Baileys Bridge** (port 8081):
   ```bash
   cd whatsapp-mcp/baileys-bridge
   npm install
   npm run build
   npm start
   ```

3. **Connect WhatsApp** (scan QR code on both bridges)

## Running Tests

### T050: Privacy Operations Test

Tests all privacy features across Go and Baileys bridges:

```bash
# With devenv
cd whatsapp-mcp/tests/e2e
python test_privacy.py

# Without devenv
python3 test_privacy.py
```

**What it tests:**
- ✓ Backend health checks
- ✓ Block/unblock contacts (Go)
- ✓ Get blocked contacts list (Go)
- ✓ Get/update privacy settings (Go)
  - Last seen privacy
  - Profile picture privacy
  - Status privacy
  - Online status privacy
- ✓ Get/update read receipts privacy (Baileys)
- ✓ Settings persistence verification

### T056: Newsletter Operations Test

Tests all newsletter features via Go bridge:

```bash
# With devenv
cd whatsapp-mcp/tests/e2e
python test_newsletters.py

# Without devenv
python3 test_newsletters.py
```

**What it tests:**
- ✓ Backend health checks (Go + Baileys)
- ✓ Create newsletter (Go)
- ✓ Get newsletter metadata (Go)
- ✓ Subscribe to newsletter (Go)
- ✓ React to newsletter message (Go)
- ✓ Unsubscribe from newsletter (Go)

**Expected Output:**
```
╔═══════════════════════════════════════════════════════╗
║   T050: Privacy Operations Integration Test          ║
╚═══════════════════════════════════════════════════════╝

=== Checking Backend Health ===
✓ PASS | Go Bridge Health
      Status: ok, Connected: True
✓ PASS | Baileys Bridge Health
      Status: ok, Connected: True

=== Testing Block Contact ===
✓ PASS | Block Contact
      Response: Contact blocked successfully, JID: 1234567890@s.whatsapp.net

...

╔═══════════════════════════════════════════════════════╗
║   Test Summary                                        ║
╚═══════════════════════════════════════════════════════╝

Total Tests: 15
Passed: 15
Failed: 0
Success Rate: 100.0%

═══════════════════════════════════════════════════════
✓ T050 INTEGRATION TEST PASSED
  All privacy operations work correctly
```

## Test Configuration

Edit test files to configure:

```python
# Test JIDs
TEST_JID = "1234567890@s.whatsapp.net"  # Valid WhatsApp JID
TEST_PHONE = "1234567890"               # Valid phone number

# Backend URLs
GO_BRIDGE_URL = "http://localhost:8080"
BAILEYS_BRIDGE_URL = "http://localhost:8081"
```

## Acceptance Criteria

Tests pass when:
- All privacy operations complete successfully
- Settings persist across operations
- Routing to correct backend (Go vs Baileys)
- No errors or exceptions

## Notes

- Tests require active WhatsApp connection
- Some tests modify real WhatsApp settings
- Use test accounts for safety
- Tests include 1-second delays to avoid rate limiting
- Blocked contacts are unblocked at end of test
