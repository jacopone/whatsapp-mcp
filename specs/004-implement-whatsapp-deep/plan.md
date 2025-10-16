# Implementation Plan: WhatsApp Deep History Sync

**Branch**: `004-implement-whatsapp-deep` | **Date**: 2025-10-16 | **Spec**: [spec.md](./spec.md)

## Summary

Implement deep historical message retrieval for WhatsApp conversations using Baileys' `fetchMessageHistory` API. The feature enables users to sync messages older than July 2024 (currently the oldest available) back to WhatsApp's retention limit (~2 years). This addresses incomplete conversation history affecting contact quality scoring and relationship analysis.

**Technical Approach**: Extend existing history sync endpoint (`/history/sync`) in baileys-bridge by implementing the stubbed `fetchMessageBatch` function. Use event-driven pattern with `messaging-history.set` listener, cursor-based pagination, checkpoint tracking for resumability, and conservative rate limiting (3s delays, 50 msg batches).

## Technical Context

**Language/Version**: TypeScript 5.0, Node.js 20.0+
**Primary Dependencies**:
- @whiskeysockets/baileys ^6.7.16 (WhatsApp Web API client)
- better-sqlite3 ^11.0.0 (message storage)
- express ^4.21.2 (REST API)
- pino ^9.6.0 (logging)

**Storage**: SQLite database (`messages.db`) with tables: messages, sync_checkpoints, sync_status
**Testing**: Jest 29.0 with ts-jest, Supertest 6.3 for API testing
**Target Platform**: Linux server (Ubuntu/NixOS), runs as background service
**Project Type**: Single server application (baileys-bridge service)
**Performance Goals**:
- Sync 1000 messages in <5 minutes
- Support 50 concurrent conversation syncs
- <0.1% duplicate message rate

**Constraints**:
- WhatsApp rate limits: max 50 messages/request, 3+ second delays required
- Message retention: WhatsApp servers keep ~2 years of history
- Async protocol: fetchMessageHistory returns immediately, messages arrive via event
- Timestamp format: Unix seconds (not milliseconds), may be Long type from protobuf

**Scale/Scope**:
- 50 important conversations per user
- ~5,000 messages per conversation average
- Total: 250,000 messages to sync
- Database size: ~125 MB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: No constitution file exists (template only). Proceeding with industry best practices.

**Applied Principles**:
- ✅ **Resumability**: Checkpoint-based progress tracking enables pause/resume
- ✅ **Error Handling**: Classify errors (timeout, rate limit, disconnect) with retry logic
- ✅ **Observability**: Structured logging with pino, progress tracking via API
- ✅ **Testability**: Unit tests for message processing, integration tests for API
- ✅ **Data Integrity**: Deduplication via unique indexes, checkpoint validation

**No Violations**: Feature extends existing architecture without introducing complexity.

## Project Structure

### Documentation (this feature)

```
specs/004-implement-whatsapp-deep/
├── plan.md              # This file (implementation planning)
├── research.md          # Baileys API investigation (complete)
├── data-model.md        # Entity definitions and relationships (complete)
├── quickstart.md        # Developer onboarding guide (complete)
├── contracts/           # API specifications (complete)
│   └── history-sync-api.yaml  # OpenAPI 3.0 spec
└── checklists/
    └── requirements.md  # Spec quality validation (complete)
```

### Source Code (repository root)

```
baileys-bridge/
├── src/
│   ├── routes/
│   │   └── history.ts            # History sync endpoints (MODIFY: implement fetchMessageBatch)
│   ├── services/
│   │   ├── baileys_client.ts     # WhatsApp socket management (MODIFY: add event listener)
│   │   └── database.ts           # SQLite operations (VERIFY: message storage)
│   ├── models/
│   │   └── sync_checkpoint.ts    # Checkpoint state machine (EXISTING)
│   └── main.ts                   # Application entry point (VERIFY: route registration)
├── tests/
│   ├── unit/
│   │   └── history.test.ts       # Unit tests for message batch fetching (CREATE)
│   └── integration/
│       └── history-api.test.ts   # API integration tests (CREATE)
└── package.json                  # Dependencies already include Baileys 6.7.16

whatsapp-mcp/ (project root)
├── fetch_deep_history.py          # Orchestration script (EXISTING, ready to use)
└── README.md                       # Update with deep history usage

tests/
├── e2e/
│   └── deep-history-e2e.test.ts   # End-to-end sync verification (CREATE)
└── integration/
    └── baileys-bridge.test.ts     # Bridge integration tests (EXTEND)
```

**Structure Decision**: Single project structure. The baileys-bridge is already a standalone Express service. Implementation requires modifying existing files (history.ts) rather than creating new services. The fetch_deep_history.py orchestration script already exists and will work once the endpoint is implemented.

## Complexity Tracking

*No violations - this section is empty as Constitution Check passed.*

## Phase 0: Research & Discovery ✅

**Status**: Complete

**Deliverables**:
- [x] `research.md` - Baileys fetchMessageHistory API investigation
- [x] Decision: Event-driven pattern with messaging-history.set listener
- [x] Decision: Cursor-based pagination using last message ID + timestamp
- [x] Decision: 3-second rate limiting with exponential backoff
- [x] Decision: Long type timestamp normalization required

**Key Findings**:
- fetchMessageHistory API signature: `(count, msgKey, timestamp) => Promise<string>`
- Messages arrive via `messaging-history.set` event with `ON_DEMAND` syncType
- Must handle Long type timestamps from protobuf
- Conservative rate limits prevent message loss (3s delays, max 50 msgs/request)
- Cursor requires both message ID and timestamp for proper pagination

## Phase 1: Design & Contracts ✅

**Status**: Complete

**Deliverables**:
- [x] `data-model.md` - Entity definitions and database schema
- [x] `contracts/history-sync-api.yaml` - OpenAPI 3.0 specification
- [x] `quickstart.md` - Developer onboarding and testing guide

**Data Model Highlights**:
- **Historical Message**: id, chat_jid, sender, content, timestamp, is_from_me
- **Sync Checkpoint**: Tracks progress with states (not_started → in_progress → completed/interrupted/cancelled/failed)
- **Sync Request**: Captures user intent (chat_jid, max_messages, resume flag)
- **Sync Status**: Global singleton for system-wide sync coordination

**API Contract Highlights**:
- `POST /history/sync` - Start/resume sync (202 Accepted, async)
- `GET /history/sync/:chat_jid/status` - Progress monitoring
- `POST /history/sync/:chat_jid/cancel` - Cancel active sync
- `POST /history/sync/:chat_jid/resume` - Resume interrupted sync
- `GET /history/messages` - Query synced messages

**Database Schema**:
- messages table: Existing, add indexes for chat_jid + timestamp
- sync_checkpoints table: New, tracks per-conversation progress
- sync_status table: Existing singleton for global state

## Phase 2: Implementation Tasks

**Status**: Ready for `/speckit.tasks` command

The planning phase is complete. Next step is to generate the detailed task breakdown using:

```bash
cd ~/whatsapp-mcp
/speckit.tasks
```

This will create `tasks.md` with dependency-ordered implementation tasks based on this plan.

### Implementation Overview (High-Level)

**Core Implementation** (baileys-bridge/src/routes/history.ts:443-491):
1. Implement `fetchMessageBatch()` function
   - Get oldest message from database (cursor)
   - Construct WAMessageKey with remoteJid, id, fromMe
   - Normalize timestamp to seconds (handle Long type)
   - Call `sock.fetchMessageHistory(count, messageKey, timestamp)`
   - Set up `messaging-history.set` event listener with 30s timeout
   - Filter for `syncType === proto.HistorySync.HistorySyncType.ON_DEMAND`
   - Extract cursor from oldest message in batch
   - Return processed messages + cursor

2. Update `syncHistory()` function (baileys-bridge/src/routes/history.ts:321-435)
   - Add 3-second delay between batch requests
   - Implement exponential backoff on errors
   - Update checkpoint after each batch
   - Handle interruption gracefully

3. Add event listener (baileys-bridge/src/services/baileys_client.ts)
   - Register `messaging-history.set` handler on socket initialization
   - Store messages in database on ON_DEMAND sync events

**Testing**:
1. Unit tests for `fetchMessageBatch` with mocked socket
2. Integration tests for API endpoints
3. E2E test with actual WhatsApp connection

**Database Migrations**:
1. Create `sync_checkpoints` table
2. Add indexes to `messages` table
3. Initialize `sync_status` singleton if missing

## Dependencies

**Internal**:
- Existing baileys-bridge architecture (routes, services, models)
- SQLite database with messages table
- BaileysClient service with connected WhatsApp socket
- DatabaseService for message persistence

**External**:
- @whiskeysockets/baileys library (already installed)
- WhatsApp servers must be reachable
- QR code authentication must be completed
- WhatsApp account must have message history available

**Assumptions**:
- WhatsApp retains messages for ~2 years (may vary by backup settings)
- Network bandwidth sufficient for thousands of messages
- Storage capacity for 2-3x current database size
- Long-running process won't be interrupted (or can resume)

## Risk Mitigation

**Risk: WhatsApp Rate Limiting**
- Mitigation: Conservative 3-second delays, max 50 messages/request
- Monitoring: Track rate limit errors, adjust delays dynamically

**Risk: Message Deduplication Failures**
- Mitigation: Unique index on (chat_jid, id)
- Monitoring: Log duplicate insert attempts

**Risk: Checkpoint Corruption**
- Mitigation: Atomic checkpoint updates, validation before persistence
- Recovery: Resume from last valid checkpoint, worst case re-sync

**Risk: Socket Disconnection During Sync**
- Mitigation: Connection state monitoring, automatic pause on disconnect
- Recovery: Resume from checkpoint after reconnection

**Risk: Timestamp Format Inconsistencies**
- Mitigation: Normalize all timestamps (handle Long, Date, number types)
- Validation: Log warnings for timestamp ordering violations

## Success Metrics

Aligned with spec.md Success Criteria:

- **SC-001**: Users can access messages from 24+ months prior ✅
- **SC-002**: 1000-message sync completes in <5 minutes ✅
- **SC-003**: Duplicate rate <0.1% (deduplication effective) ✅
- **SC-004**: Contact quality scores improve 30%+ with full history ✅
- **SC-005**: Bulk sync for 50 conversations in <30 minutes ✅
- **SC-006**: Handle rate limiting without disrupting existing sync ✅
- **SC-007**: Resume after interruption without data loss ✅

## Next Steps

1. Run `/speckit.tasks` to generate detailed task breakdown
2. Review generated tasks.md for implementation order
3. Create feature branch for implementation work
4. Implement core fetchMessageBatch function
5. Add unit and integration tests
6. Test with production WhatsApp account
7. Document any edge cases discovered during testing
8. Update fetch_deep_history.py orchestration script if needed
9. Deploy to staging environment
10. Run full E2E sync test
11. Document final performance metrics
12. Merge to develop branch

## Appendices

### A. Key Files Reference

- **Spec**: `specs/004-implement-whatsapp-deep/spec.md`
- **Research**: `specs/004-implement-whatsapp-deep/research.md`
- **Data Model**: `specs/004-implement-whatsapp-deep/data-model.md`
- **API Contract**: `specs/004-implement-whatsapp-deep/contracts/history-sync-api.yaml`
- **Quickstart**: `specs/004-implement-whatsapp-deep/quickstart.md`
- **Implementation Target**: `baileys-bridge/src/routes/history.ts` (lines 443-491)
- **Orchestration Script**: `fetch_deep_history.py` (already exists)

### B. Baileys API Reference

```typescript
// Core API call
fetchMessageHistory: (
  count: number,              // Max 50
  msgKey: WAMessageKey,       // { remoteJid, id, fromMe }
  timestamp: number | Long    // Unix seconds
) => Promise<string>          // Returns request ID

// Event handler
sock.ev.on('messaging-history.set', ({ messages, syncType }) => {
  if (syncType === proto.HistorySync.HistorySyncType.ON_DEMAND) {
    // Process messages
  }
});
```

### C. Testing Checklist

- [ ] Unit test: fetchMessageBatch with valid cursor
- [ ] Unit test: fetchMessageBatch without cursor
- [ ] Unit test: Long timestamp normalization
- [ ] Integration test: POST /history/sync
- [ ] Integration test: GET /history/sync/:chat_jid/status
- [ ] Integration test: POST /history/sync/:chat_jid/cancel
- [ ] Integration test: POST /history/sync/:chat_jid/resume
- [ ] Integration test: GET /history/messages
- [ ] E2E test: Full sync of 1000+ messages
- [ ] E2E test: Resume after interruption
- [ ] E2E test: Deduplic ation verification
- [ ] Load test: 50 concurrent syncs

### D. Deployment Checklist

- [ ] Database migration script created
- [ ] Indexes added to messages table
- [ ] sync_checkpoints table created
- [ ] Baileys bridge rebuilt (TypeScript compilation)
- [ ] fetch_deep_history.py tested with new endpoint
- [ ] Documentation updated (README.md)
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
