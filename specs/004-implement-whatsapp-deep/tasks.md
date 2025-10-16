# Tasks: WhatsApp Deep History Sync

**Input**: Design documents from `/home/guyfawkes/whatsapp-mcp/specs/004-implement-whatsapp-deep/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/history-sync-api.yaml

**Tests**: Not explicitly requested in spec - tasks focus on implementation

**Organization**: Tasks grouped by user story (P1, P2, P3) for independent implementation

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story this task belongs to (US1, US2, US3)
- All paths relative to `~/whatsapp-mcp/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database schema and type definitions needed by all user stories

- [ ] T001 [P] Create database migration script for sync_checkpoints table in `baileys-bridge/migrations/001_add_sync_checkpoints.sql`
- [ ] T002 [P] Add database indexes to messages table in `baileys-bridge/migrations/002_add_message_indexes.sql`
- [ ] T003 [P] Import Long type from 'long' package in `baileys-bridge/src/routes/history.ts`

**SQL for T001** (sync_checkpoints table):
```sql
CREATE TABLE IF NOT EXISTS sync_checkpoints (
  sync_id TEXT PRIMARY KEY,
  chat_jid TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'interrupted', 'cancelled', 'completed', 'failed')),
  messages_synced INTEGER NOT NULL DEFAULT 0,
  last_message_id TEXT,
  last_timestamp DATETIME,
  progress_percent INTEGER CHECK(progress_percent BETWEEN 0 AND 100),
  error_message TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME
);

CREATE INDEX idx_sync_checkpoints_status ON sync_checkpoints(status);
CREATE INDEX idx_sync_checkpoints_chat_jid ON sync_checkpoints(chat_jid);
```

**SQL for T002** (message indexes):
```sql
CREATE INDEX IF NOT EXISTS idx_messages_chat_jid ON messages(chat_jid);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_msg ON messages(chat_jid, id);
```

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and helper functions that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create timestamp normalization utility function `normalizeTimestamp()` in `baileys-bridge/src/routes/history.ts`
- [ ] T005 Create message content extraction utility function `extractMessageContent()` in `baileys-bridge/src/routes/history.ts`
- [ ] T006 [P] Add database method `getOldestMessage(chat_jid)` in `baileys-bridge/src/services/database.ts`
- [ ] T007 [P] Add database method `messageExists(chat_jid, message_id)` in `baileys-bridge/src/services/database.ts`

**T004 Implementation**:
```typescript
function normalizeTimestamp(ts: Date | number | Long): number {
  if (ts instanceof Date) {
    return Math.floor(ts.getTime() / 1000);
  }
  return Long.isLong(ts) ? ts.toNumber() : ts;
}
```

**T005 Implementation**:
```typescript
function extractMessageContent(msg: proto.IWebMessageInfo): string {
  const message = msg.message;
  if (!message) return '';

  if (message.conversation) return message.conversation;
  if (message.extendedTextMessage?.text) return message.extendedTextMessage.text;
  if (message.imageMessage?.caption) return `[Image: ${message.imageMessage.caption}]`;
  if (message.videoMessage?.caption) return `[Video: ${message.videoMessage.caption}]`;
  if (message.documentMessage?.caption) return `[Document: ${message.documentMessage.caption}]`;

  return '[Non-text message]';
}
```

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Access Complete Message History (Priority: P1) 🎯 MVP

**Goal**: Enable fetching historical messages for a single conversation using Baileys fetchMessageHistory API

**Independent Test**: Request historical messages for one contact, verify messages older than July 2024 are retrieved and stored in database

### Implementation for User Story 1

**Core API Implementation** (baileys-bridge/src/routes/history.ts):

- [ ] T008 [US1] Implement `waitForHistoryMessages()` helper function in `baileys-bridge/src/routes/history.ts` (lines 492-520)
  - Set up Promise with 30-second timeout
  - Register `messaging-history.set` event listener
  - Filter for `syncType === proto.HistorySync.HistorySyncType.ON_DEMAND`
  - Extract cursor from oldest message in batch
  - Return processed messages array + cursor
  - Clean up event listener on completion/timeout

- [ ] T009 [US1] Implement `fetchMessageBatch()` function in `baileys-bridge/src/routes/history.ts` (lines 443-491)
  - Validate oldestMessageId and oldestTimestamp parameters
  - Limit count to max 50 (WhatsApp's hard limit)
  - Construct WAMessageKey: `{ remoteJid, id, fromMe }`
  - Normalize timestamp using `normalizeTimestamp()` from T004
  - Call `sock.fetchMessageHistory(count, messageKey, timestamp)`
  - Wait for messages using `waitForHistoryMessages()` from T008
  - Process messages with `extractMessageContent()` from T005
  - Return `{ messages, cursor }` object

- [ ] T010 [US1] Update `syncHistory()` function in `baileys-bridge/src/routes/history.ts` (lines 321-435)
  - Add RATE_LIMIT_DELAY_MS = 3000 constant
  - Query oldest message using `getOldestMessage()` from T006 for initial cursor
  - Pass oldestMessageId AND oldestTimestamp to fetchMessageBatch()
  - Add 3-second delay: `await new Promise(resolve => setTimeout(resolve, 3000))` after each batch
  - Implement exponential backoff on errors (3s → 6s → 12s for up to 3 retries)
  - Update checkpoint timestamp from batch messages
  - Handle Long timestamp conversion using `normalizeTimestamp()`

**Event Listener Registration** (baileys-bridge/src/services/baileys_client.ts):

- [ ] T011 [US1] Register `messaging-history.set` event handler in BaileysClient socket initialization
  - Add event listener in `makeWASocket()` configuration
  - Filter for `syncType === proto.HistorySync.HistorySyncType.ON_DEMAND`
  - Log received message count and sync type
  - Note: Actual message storage handled by `waitForHistoryMessages()` in routes/history.ts

**Testing & Validation**:

- [ ] T012 [US1] Create manual test script `baileys-bridge/test-single-sync.sh`
  - Start baileys-bridge: `npm run dev`
  - POST to `/history/sync` with single chat_jid and max_messages=100
  - Poll `/history/sync/:chat_jid/status` every 5 seconds
  - Query `/history/messages?chat_jid=...&limit=50` when complete
  - Verify messages older than July 2024 are present
  - Verify no duplicate messages exist
  - Log SUCCESS or FAILURE with diagnostics

**Checkpoint**: At this point, User Story 1 should be fully functional - single conversation history sync works end-to-end

---

## Phase 4: User Story 2 - Bulk Historical Sync (Priority: P2)

**Goal**: Enable syncing historical messages for multiple conversations simultaneously

**Independent Test**: Provide list of 5-10 chat_jids, verify all are queued and sync completes for all conversations

### Implementation for User Story 2

**Bulk Sync Endpoint** (baileys-bridge/src/routes/history.ts):

- [ ] T013 [US2] Add `POST /history/sync/bulk` endpoint in `baileys-bridge/src/routes/history.ts`
  - Accept `{ chat_jids: string[], max_messages?: number }` request body
  - Validate chat_jids array (non-empty, valid JID format)
  - Limit to max 50 chat_jids per request
  - Loop through chat_jids and create individual sync requests
  - Return `{ queued: number, sync_ids: string[] }` response
  - Use existing `POST /history/sync` logic for each conversation

- [ ] T014 [US2] Add `GET /history/sync/bulk/status` endpoint in `baileys-bridge/src/routes/history.ts`
  - Accept `sync_ids[]` query parameter (array of chat_jids)
  - Query checkpoint status for all provided sync_ids
  - Aggregate: total syncs, completed, in_progress, failed counts
  - Calculate overall progress percentage
  - Return `{ total, completed, in_progress, failed, progress_percent, checkpoints: [] }`

**Orchestration Script Enhancement** (fetch_deep_history.py):

- [ ] T015 [US2] Update `fetch_deep_history.py` to use bulk endpoint
  - Read chat_jids from oldest messages query (limit 50)
  - POST to `/history/sync/bulk` instead of individual requests
  - Poll `/history/sync/bulk/status` for progress
  - Display progress bar using `rich.progress`
  - Log failed syncs with error messages
  - Retry failed syncs individually after bulk completion

**Testing & Validation**:

- [ ] T016 [US2] Create bulk test script `baileys-bridge/test-bulk-sync.sh`
  - Query database for 10 chat_jids with oldest messages
  - POST to `/history/sync/bulk` with all 10 chat_jids
  - Poll `/history/sync/bulk/status` until complete
  - Verify all 10 conversations have synced messages
  - Check that syncs ran sequentially (3s delays observed)
  - Log SUCCESS with timing statistics

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - single and bulk sync are independently functional

---

## Phase 5: User Story 3 - Progress Monitoring and Error Handling (Priority: P3)

**Goal**: Provide detailed progress tracking, error classification, and graceful error recovery

**Independent Test**: Start sync, monitor real-time progress, intentionally disconnect WhatsApp, verify graceful handling and resume capability

### Implementation for User Story 3

**Enhanced Progress Tracking**:

- [ ] T017 [P] [US3] Add progress percentage calculation to `syncHistory()` in `baileys-bridge/src/routes/history.ts`
  - Calculate: `(messagesFetched / maxMessages) * 100`
  - Update checkpoint.progress_percent every CHECKPOINT_INTERVAL (100 messages)
  - Include estimated time remaining based on current sync rate
  - Log progress milestones: 25%, 50%, 75%, 100%

- [ ] T018 [P] [US3] Enhance `GET /history/sync/:chat_jid/status` response in `baileys-bridge/src/routes/history.ts`
  - Add `estimated_completion_time` field (calculate from sync rate)
  - Add `messages_per_second` metric
  - Add `oldest_message_date` from checkpoint
  - Add `error_details` object if status is failed/interrupted

**Error Classification and Handling**:

- [ ] T019 [US3] Create error classification utility in `syncHistory()` function
  - Classify timeout errors: `TIMEOUT: WhatsApp did not respond`
  - Classify rate limit errors: `RATE_LIMIT: Too many requests`
  - Classify disconnect errors: `DISCONNECTED: Socket not available`
  - Classify invalid key errors: `INVALID_KEY: Message not found`
  - Set checkpoint.error_message with classified error
  - Log error type and retry strategy

- [ ] T020 [US3] Implement connection state monitoring in `baileys-bridge/src/services/baileys_client.ts`
  - Listen to `connection.update` event
  - On `connection === 'close'`: Pause all active syncs
  - Save checkpoints for all in-progress syncs
  - Set sync status to 'interrupted'
  - Log disconnect event with active sync count

**Automatic Retry Logic**:

- [ ] T021 [US3] Add exponential backoff retry in `syncHistory()` function
  - MAX_RETRIES = 3 constant
  - On error: Calculate backoff = RATE_LIMIT_DELAY_MS * Math.pow(2, retryCount)
  - Wait backoff duration before retry
  - Update checkpoint with retry count
  - If all retries fail: Set status to 'failed' with error details

**Resume After Interruption**:

- [ ] T022 [US3] Enhance `POST /history/sync/:chat_jid/resume` endpoint
  - Query checkpoint from database
  - Validate checkpoint can be resumed (status: interrupted, cancelled)
  - Restore cursor from checkpoint.last_message_id and checkpoint.last_timestamp
  - Continue sync from last known position
  - Update status from 'interrupted' to 'in_progress'
  - Log resume event with messages already synced

**Testing & Validation**:

- [ ] T023 [US3] Create error handling test script `baileys-bridge/test-error-handling.sh`
  - Start sync for conversation
  - After 50 messages, kill baileys-bridge process (simulate crash)
  - Restart baileys-bridge
  - POST to `/history/sync/:chat_jid/resume`
  - Verify sync continues from checkpoint without duplicates
  - Verify final message count is correct
  - Log SUCCESS if resume works correctly

**Checkpoint**: All user stories should now be independently functional with robust error handling

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, and final validation

- [ ] T024 [P] Update README.md with deep history sync usage examples
  - Add "Historical Message Sync" section
  - Document single sync endpoint with curl examples
  - Document bulk sync endpoint with curl examples
  - Document progress monitoring endpoints
  - Add troubleshooting section for common errors
  - Link to quickstart.md for developers

- [ ] T025 [P] Add logging improvements across all endpoints
  - Log sync start with chat_jid and max_messages
  - Log batch completion with messages fetched
  - Log checkpoint saves with progress percentage
  - Log errors with full error object and stack trace
  - Log sync completion with total time and message count

- [ ] T026 Run database migrations from Phase 1
  - Execute 001_add_sync_checkpoints.sql
  - Execute 002_add_message_indexes.sql
  - Verify tables and indexes created successfully
  - Check index performance with EXPLAIN QUERY PLAN

- [ ] T027 Build TypeScript and verify no compilation errors
  - Run `npm run build` in baileys-bridge/
  - Fix any type errors related to Long, WAMessageKey, proto types
  - Verify dist/ directory contains compiled JavaScript

- [ ] T028 Run quickstart.md validation procedures
  - Follow "Quick Test (5 minutes)" section step-by-step
  - Verify all curl commands work as documented
  - Verify example responses match actual API responses
  - Update quickstart.md if any discrepancies found

- [ ] T029 Create deployment checklist in `DEPLOYMENT.md`
  - Pre-deployment: Database backups
  - Migration: Run SQL scripts
  - Deployment: Rebuild TypeScript, restart service
  - Validation: Run test-single-sync.sh
  - Rollback: Restore database, revert code
  - Monitoring: Check logs for errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
  - T001, T002, T003 can all run in parallel [P]
- **Foundational (Phase 2)**: Depends on Setup (T003 for Long import) - BLOCKS all user stories
  - T004, T005 sequential (same file)
  - T006, T007 can run in parallel [P] (different methods)
- **User Story 1 (Phase 3)**: Depends on Foundational completion
  - T008 → T009 → T010 sequential (same file, dependencies)
  - T011 independent (different file), can run parallel with T008-T010
  - T012 after all implementation complete
- **User Story 2 (Phase 4)**: Depends on User Story 1 (reuses sync logic)
  - T013 → T014 sequential (same file)
  - T015 can run in parallel with T013-T014 [P] (different file)
  - T016 after all implementation complete
- **User Story 3 (Phase 5)**: Depends on User Story 1 (enhances sync function)
  - T017, T018 can run in parallel [P] (different concerns)
  - T019 → T021 sequential (same function)
  - T020, T022 independent, can run parallel
  - T023 after all implementation complete
- **Polish (Phase 6)**: Depends on all user stories complete
  - T024, T025 can run in parallel [P]
  - T026-T029 sequential (validation steps)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on User Story 1 - Reuses single sync logic for bulk operations
- **User Story 3 (P3)**: Depends on User Story 1 - Enhances existing sync with monitoring/errors

### Critical Path

Setup → Foundational → US1 Core (T008-T010) → US2 Bulk (T013-T014) → US3 Monitoring (T017-T022) → Polish

**Estimated Duration**:
- Setup: 1 hour (database migrations, imports)
- Foundational: 2 hours (utility functions, database methods)
- User Story 1: 6-8 hours (core fetchMessageHistory implementation)
- User Story 2: 3-4 hours (bulk endpoint and orchestration)
- User Story 3: 4-5 hours (progress tracking, error handling)
- Polish: 2-3 hours (documentation, validation)
- **Total: 18-23 hours** for complete implementation

### Parallel Opportunities

- **Phase 1 Setup**: All 3 tasks can run in parallel
- **Phase 2 Foundational**: T006, T007 database methods can run in parallel
- **Phase 3 US1**: T011 event listener can run parallel with T008-T010 route implementation
- **Phase 4 US2**: T015 orchestration script can run parallel with T013-T014 endpoints
- **Phase 5 US3**: T017-T018 progress tracking can run parallel, T020-T022 error handling can run parallel
- **Phase 6 Polish**: T024-T025 documentation/logging can run in parallel

---

## Parallel Example: User Story 1

```bash
# Can launch in parallel (different files):
Task T010: Update syncHistory() in baileys-bridge/src/routes/history.ts
Task T011: Register event handler in baileys-bridge/src/services/baileys_client.ts

# Must run sequentially (same file, dependencies):
Task T008: waitForHistoryMessages() helper
  ↓
Task T009: fetchMessageBatch() implementation (uses T008)
  ↓
Task T010: syncHistory() enhancement (uses T009)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003) - Database schema ready
2. Complete Phase 2: Foundational (T004-T007) - Utilities ready
3. Complete Phase 3: User Story 1 (T008-T012) - Single conversation sync works
4. **STOP and VALIDATE**: Run test-single-sync.sh, verify messages retrieved
5. Deploy to staging, test with production WhatsApp account
6. **MVP Ready**: Can sync historical messages for any conversation!

### Incremental Delivery

1. **Week 1**: Setup + Foundational + User Story 1 → Single sync MVP
2. **Week 2**: User Story 2 → Bulk sync capability added
3. **Week 3**: User Story 3 → Robust error handling and monitoring
4. **Week 4**: Polish → Production-ready deployment

### Suggested Checkpoints

- ✅ After T007: Run `npm run build`, verify no type errors
- ✅ After T010: Test fetchMessageBatch() with single conversation
- ✅ After T012: Full User Story 1 validation
- ✅ After T016: Bulk sync validation with 10 conversations
- ✅ After T023: Error handling validation with simulated failures
- ✅ After T029: Final deployment readiness check

---

## Notes

- **[P] tasks** = different files, no dependencies, safe to parallelize
- **[Story] label** = maps task to user story for traceability (US1, US2, US3)
- **Each user story is independently deliverable** = can ship US1 without US2/US3
- **Commit frequently**: After each task or logical group of changes
- **Test at checkpoints**: Don't wait until end to discover issues
- **Follow quickstart.md**: Use as validation guide during development
- **Database first**: Run migrations before any code changes
- **Type safety**: Fix TypeScript errors immediately, don't accumulate technical debt

**Key Files Modified**:
- `baileys-bridge/src/routes/history.ts` (T008-T010, T013-T014, T017-T019, T021-T022)
- `baileys-bridge/src/services/baileys_client.ts` (T011, T020)
- `baileys-bridge/src/services/database.ts` (T006-T007)
- `fetch_deep_history.py` (T015)
- `README.md` (T024)

**Total Tasks**: 29 tasks across 6 phases
- Phase 1 Setup: 3 tasks
- Phase 2 Foundational: 4 tasks
- Phase 3 User Story 1 (MVP): 5 tasks
- Phase 4 User Story 2: 4 tasks
- Phase 5 User Story 3: 7 tasks
- Phase 6 Polish: 6 tasks
