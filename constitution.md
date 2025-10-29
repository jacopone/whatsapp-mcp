# WhatsApp MCP Server - Project Constitution

---
status: active
created: 2025-10-10
updated: 2025-10-10
type: architecture
lifecycle: persistent
---

## Project Purpose

Build a comprehensive WhatsApp automation server using the Model Context Protocol (MCP) that enables AI agents to interact with WhatsApp for personal productivity, relationship management, and communication automation.

## Core Principles

### 1. Best-of-Breed Integration
**Principle**: Don't choose between libraries - use the best implementation for each capability.

**Rationale**: WhatsApp supports multiple linked devices. We can run multiple backend implementations simultaneously and route each request to the optimal backend.

**Application**:
- Use whatsmeow (Go) for stable, core operations and features only it supports (communities)
- Use Baileys (TypeScript) for features it handles better (history sync, advanced polls, status)
- Route intelligently based on feature capabilities, not arbitrary preferences

### 2. Data Integrity First
**Principle**: Maintain a single source of truth with reliable synchronization.

**Rationale**: Multiple backends mean multiple potential data sources. Confusion and data loss are unacceptable.

**Application**:
- Go bridge database (`messages.db`) is the canonical source of truth
- Baileys uses temporary storage only during sync operations
- All sync operations include deduplication and validation
- Schema transformations are tested and reversible
- No data is discarded without explicit user control

### 3. Graceful Degradation
**Principle**: Features should degrade gracefully when backends are unavailable.

**Rationale**: One backend failure shouldn't break the entire system.

**Application**:
- Health checks before routing decisions
- Fallback to alternative backend when possible
- Clear error messages indicating which backend failed
- Continue-on-error for bulk operations
- Manual override options for routing decisions

### 4. Transparent Operations
**Principle**: Users should understand what's happening and why.

**Rationale**: WhatsApp automation can have privacy and security implications.

**Application**:
- Log all routing decisions (which backend handled what)
- Expose sync status and progress
- Show which messages came from which backend
- Provide clear error messages with actionable guidance
- Document rate limits and API constraints

### 5. Privacy by Design
**Principle**: Minimize data retention and maximize user control.

**Rationale**: WhatsApp messages contain sensitive personal information.

**Application**:
- Temporary Baileys database cleared after sync completion
- No cloud uploads without explicit user configuration
- Local-only processing by default
- Clear data retention policies
- User-controlled message history limits
- Encryption at rest for authentication credentials

### 6. Performance Matters
**Principle**: Optimize for responsiveness in interactive AI workflows.

**Rationale**: AI agents need fast responses to maintain conversation flow.

**Application**:
- Message sending: < 1 second response time
- Database queries: < 100ms for common patterns
- History sync: Asynchronous with progress reporting
- Concurrent backend operations when safe
- Lazy loading for large result sets
- Connection pooling and keepalive

### 7. Idiomatic Implementation
**Principle**: Use each language's strengths and conventions.

**Rationale**: Fighting language idioms creates bugs and maintenance burden.

**Application**:
- Go: Use channels, goroutines, error returns
- TypeScript: Use promises, async/await, event emitters
- Python: Use type hints, context managers, generators
- Don't try to make Python look like Go or vice versa
- Embrace each ecosystem's best practices

### 8. Test-Driven Reliability
**Principle**: Critical paths require automated testing.

**Rationale**: Integration between multiple backends creates complexity that manual testing can't cover.

**Application**:
- Unit tests for routing logic
- Integration tests for each backend client
- End-to-end tests for hybrid workflows (history sync → mark as read)
- Mock backends for testing orchestration logic
- Regression tests for each bug fix
- Performance benchmarks for critical operations

### 9. Documentation as Code
**Principle**: Documentation must be maintained alongside code changes.

**Rationale**: Multiple backends and intelligent routing require clear documentation to understand system behavior.

**Application**:
- API reference generated from code annotations
- Routing decisions documented in code comments
- Architecture diagrams in version control
- CHANGELOG.md updated with each release
- Examples tested as part of CI/CD
- Troubleshooting guide based on real issues

### 10. Incremental Value Delivery
**Principle**: Ship working features frequently rather than big bang releases.

**Rationale**: Early feedback prevents building the wrong thing.

**Application**:
- Phase 1: Baileys history sync + Go mark as read (immediate user value)
- Phase 2: Additional Baileys features (polls, status)
- Phase 3: Complete Go feature set (groups, newsletters)
- Phase 4: Advanced features and optimizations
- Each phase deployable and usable independently

## Design Decisions

### Architecture: Orchestrator Pattern
**Decision**: Python orchestrator coordinates between Go and TypeScript backends.

**Alternatives Considered**:
- Monolith in single language → Rejected: No library has all features
- Direct MCP in Go/TypeScript → Rejected: Too much duplication
- Microservices with message queue → Rejected: Overcomplicated for single-user

**Rationale**:
- Python MCP server is already working and familiar
- Orchestrator keeps routing logic in one place
- HTTP clients easier than native FFI bindings
- Each backend can evolve independently

### Database: SQLite with Single Source of Truth
**Decision**: Go bridge owns canonical database, Baileys uses temporary storage.

**Alternatives Considered**:
- Separate databases per backend → Rejected: Synchronization complexity
- Shared PostgreSQL → Rejected: Deployment complexity
- No database, API-only → Rejected: Poor offline capability

**Rationale**:
- SQLite: Simple, fast, embedded
- Single source of truth: Prevents conflicts
- Temporary Baileys DB: Enables sync without coupling
- File-based: Easy backup and inspection

### Communication: REST over HTTP
**Decision**: Backends expose REST APIs, orchestrator uses HTTP clients.

**Alternatives Considered**:
- gRPC → Rejected: Overkill for local communication
- Unix sockets → Rejected: Platform-specific
- Shared memory → Rejected: Requires FFI complexity

**Rationale**:
- REST: Simple, debuggable, universal
- HTTP: Testable with curl, language-agnostic
- Localhost-only: No network security concerns
- Standard ports: Easy firewall rules

## Success Criteria

### Functional Success
- AI agent can retrieve full WhatsApp history via Baileys
- AI agent can mark community as read via Go
- All 86 planned tools implemented and functional
- Hybrid workflows (history sync → mark as read) work reliably
- No data loss during synchronization operations

### Technical Success
- Both backends run simultaneously without conflicts
- Routing logic selects correct backend > 99% of time
- Database sync completes without errors
- All critical paths covered by automated tests
- < 1 second response time for message operations

### User Experience Success
- Clear documentation for all 86 tools
- Troubleshooting guide resolves common issues
- Error messages actionable and understandable
- AI agents can accomplish tasks without human intervention
- Setup process completable in < 30 minutes

## Anti-Patterns to Avoid

### ❌ Feature Duplication
Don't implement the same feature in both backends "just to have options."

**Why**: Maintenance burden, testing complexity, routing confusion.

**Instead**: Choose best backend per feature, document decision.

### ❌ Tight Coupling
Don't make backends aware of each other or the orchestrator.

**Why**: Prevents independent evolution and testing.

**Instead**: Backends expose generic APIs, orchestrator handles composition.

### ❌ Silent Failures
Don't suppress errors or hide backend failures.

**Why**: Creates mysterious behavior and data loss.

**Instead**: Fail fast, log verbosely, report errors to user.

### ❌ Premature Optimization
Don't optimize before measuring performance bottlenecks.

**Why**: Wastes time, adds complexity, may optimize wrong thing.

**Instead**: Measure first, optimize proven bottlenecks, benchmark improvements.

### ❌ Undocumented Routing Decisions
Don't route to backends without explaining why in code comments.

**Why**: Future maintainers won't understand system behavior.

**Instead**: Comment each routing decision with rationale from feature matrix.

### ❌ Big Bang Integration
Don't wait to test backends together until "everything is ready."

**Why**: Integration issues discovered late are expensive to fix.

**Instead**: Integrate continuously, test hybrid workflows from Phase 1.

## Change Control

### Constitution Updates
This constitution may be updated when:
- Core project goals change
- Architectural decisions prove incorrect
- New principles emerge from experience
- Team consensus changes

**Process**:
1. Propose change with rationale
2. Document alternatives considered
3. Review impact on existing code
4. Update affected documentation
5. Increment version number

### Principle Conflicts
When principles conflict in practice:
1. Document the specific conflict
2. Analyze which principle takes precedence in this context
3. Make decision based on project purpose
4. Update constitution if pattern repeats

## Version History

- **v1.0** (2025-10-10): Initial constitution based on COMPLETE_HYBRID_SPEC.md
