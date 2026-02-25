# wacli Migration Design

## Status: Deferred (revisit in ~2 weeks)

## Context

Replace custom Go bridge (`whatsapp-bridge/`) with wacli (https://github.com/steipete/wacli) to reduce maintenance. The current system works; this is a future simplification.

## Architecture Change

```
Before: Claude → Python MCP → HTTP localhost:8080 → Go Bridge (whatsmeow) → WhatsApp
After:  Claude → Python MCP → subprocess wacli --json → wacli (whatsmeow) → WhatsApp
```

## Corrections to MIGRATE-TO-WACLI.md

| Original assumption | Corrected |
|---|---|
| Binary name: `wa` | `wacli` |
| Nix: `fetchurl` prebuilt binary | `buildGoModule` (no Linux release binaries exist) |
| `wa chats list --json` | `wacli chats list --json` |
| `wa messages send <jid> "text"` | `wacli send text --to <jid> --message "text"` |
| `wa messages send --file` | `wacli send file --to <jid> --file <path>` |
| `wa messages search` | `wacli messages search "query" --json` |
| `wa contacts search` | No dedicated command — filter `wacli chats list --json` |
| `wa messages backfill` | `wacli history backfill --chat <jid>` |
| Download via HTTP POST | `wacli media download --chat <jid> --id <msg-id>` |

## Nix Package

Use `buildGoModule` (not `fetchurl`). Requires:
- `tags = [ "sqlite_fts5" ]`
- `CGO_ENABLED = "1"`
- Go 1.25+ (per wacli go.mod)
- Reference: gogcli.nix for style, but different builder

## Python MCP Changes

- Replace HTTP calls + direct SQLite with `subprocess.run(["wacli", ...])`
- Remove `requests`/`httpx` dependencies
- Keep `audio.py` ffmpeg logic, change only the send call
- MCP tool names and parameters stay identical

## Files to Change

- `~/nixos-config/pkgs/wacli.nix` — NEW
- `~/nixos-config/modules/core/packages.nix` — ADD reference
- `whatsapp-mcp-server/whatsapp.py` — REWRITE
- `whatsapp-mcp-server/main.py` — MINOR updates
- `whatsapp-mcp-server/audio.py` — MINOR (send call only)
- `whatsapp-mcp-server/pyproject.toml` — remove requests/httpx

## Files to Delete

- `whatsapp-bridge/` — entire directory
- `baileys-bridge/` — entire directory
- `sync_all_history.py`

## Risk

JSON output format from wacli needs verification after install. May need field-name adjustments in Python code.
