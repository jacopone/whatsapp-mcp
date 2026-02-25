# Migration: Replace Go Bridge with wacli

## Context

This project currently uses a custom Go bridge (`whatsapp-bridge/main.go`, ~1350 LOC) that connects to WhatsApp via whatsmeow and exposes an HTTP API on localhost:8080. A Python MCP server (`whatsapp-mcp-server/`) calls this HTTP API to provide WhatsApp tools to Claude.

We want to replace the custom Go bridge with **wacli** (https://github.com/steipete/wacli) — a mature, community-maintained WhatsApp CLI by steipete (same author as gogcli which we already use for Google services). This keeps us in the same ecosystem and reduces maintenance burden.

## What wacli provides that our bridge doesn't

- **FTS5 full-text search** on messages (our bridge does substring LIKE queries)
- **On-demand history backfill** per chat (our bridge does full sync only)
- **Group admin** (rename, manage participants)
- **JSON output mode** (`--json` flag) — perfect for scripting
- **Active maintenance** — 537 stars, 5 contributors, regular releases
- **Device labeling** — configurable device name

## Architecture: Before vs After

### Before (current)
```
Claude → (stdio) → Python MCP Server → (HTTP localhost:8080) → Go Bridge (whatsmeow) → WhatsApp
```

### After (target)
```
Claude → (stdio) → Python MCP Server → (subprocess: wa CLI --json) → wacli (whatsmeow) → WhatsApp
```

## Step-by-step plan

### 1. Create Nix package for wacli

Create `~/nixos-config/pkgs/wacli.nix` modeled on the existing `~/nixos-config/pkgs/gogcli.nix`:

```nix
{ lib, stdenv, fetchurl, autoPatchelfHook }:

stdenv.mkDerivation rec {
  pname = "wacli";
  version = "0.2.0";  # CHECK: get latest from https://github.com/steipete/wacli/releases

  src = fetchurl {
    url = "https://github.com/steipete/wacli/releases/download/v${version}/wacli_${version}_linux_amd64.tar.gz";
    sha256 = "";  # MUST COMPUTE: nix-prefetch-url --unpack <url>
  };

  sourceRoot = ".";
  nativeBuildInputs = [ autoPatchelfHook ];

  installPhase = ''
    install -Dm755 wa $out/bin/wa
  '';

  meta = with lib; {
    description = "WhatsApp CLI built on whatsmeow";
    homepage = "https://github.com/steipete/wacli";
    license = licenses.mit;
    platforms = [ "x86_64-linux" ];
    mainProgram = "wa";
  };
}
```

- Verify the binary name inside the tarball (likely `wa`)
- Compute sha256 with: `nix-prefetch-url --unpack https://github.com/steipete/wacli/releases/download/v0.2.0/wacli_0.2.0_linux_amd64.tar.gz`
- Add to `~/nixos-config/modules/core/packages.nix` like gogcli
- DO NOT run nixos-rebuild — tell the user to do it

### 2. Authenticate wacli

```bash
wa auth login
# Scan QR code with WhatsApp mobile
wa auth status  # verify
```

wacli stores data in `~/.wacli/` by default. Run `wa follow` once to start syncing messages.

### 3. Learn wacli CLI patterns

Key commands the MCP server will need:

```bash
# List chats
wa chats list --json

# Search messages
wa messages search "query" --json --max 50

# List messages in a chat
wa messages list <jid> --json --max 20

# Send text message
wa messages send <jid> "message text"

# Send file
wa messages send <jid> --file /path/to/file

# Get contact info
wa contacts search "name" --json

# History backfill for a specific chat
wa messages backfill <jid>
```

Test each command manually and verify JSON output structure before coding.

### 4. Rewrite Python MCP server

Modify `whatsapp-mcp-server/whatsapp.py` to call `wa` CLI via subprocess instead of HTTP requests.

Key changes:
- Replace all `requests.post("http://127.0.0.1:8080/api/send", ...)` with `subprocess.run(["wa", "messages", "send", ...])`
- Replace all SQLite direct queries with `wa` CLI calls using `--json` output
- Parse JSON output from `wa` commands instead of querying SQLite directly
- Remove the health check for localhost:8080

**Important**: The MCP server currently reads SQLite directly for queries (list_messages, search_contacts, list_chats, etc.) and only uses HTTP for sending. With wacli:
- **Reads**: Use `wa messages search --json`, `wa chats list --json`, etc.
- **Writes**: Use `wa messages send`
- **Media**: Use `wa messages send --file` for sending, check wacli docs for download

Create a helper function:
```python
import subprocess, json

def wa_command(*args) -> dict:
    """Run a wacli command and return parsed JSON output."""
    result = subprocess.run(
        ["wa", *args, "--json"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"wacli error: {result.stderr}")
    return json.loads(result.stdout)
```

### 5. Update MCP tool implementations

Map current tools to wacli commands:

| MCP Tool | Current impl | New impl (wacli) |
|----------|-------------|-------------------|
| `search_contacts` | SQLite query | `wa contacts search "name" --json` |
| `list_messages` | SQLite with filters | `wa messages list <jid> --json --max N` or `wa messages search "text" --json` |
| `list_chats` | SQLite query | `wa chats list --json` |
| `get_chat` | SQLite by JID | `wa chats list --json` + filter |
| `get_direct_chat_by_contact` | SQLite LIKE | `wa contacts search --json` + find chat |
| `send_message` | HTTP POST to bridge | `wa messages send <jid> "text"` |
| `send_file` | HTTP POST with file | `wa messages send <jid> --file /path` |
| `send_audio_message` | HTTP POST + ffmpeg | Keep ffmpeg conversion, then `wa messages send --file` |
| `download_media` | HTTP POST to bridge | Check wacli docs for media download |

### 6. Handle audio messages

The current `audio.py` converts audio to Opus .ogg format for WhatsApp voice messages. This logic should stay — it's independent of the bridge. Just change the final send step from HTTP POST to `wa messages send --file`.

### 7. Test thoroughly

- [ ] `wa` binary is in PATH after nixos-rebuild
- [ ] `wa auth login` and QR scan works
- [ ] `wa chats list --json` returns valid JSON
- [ ] `wa messages search "test" --json` works
- [ ] `wa messages send <your-own-jid> "test"` sends successfully
- [ ] All 12 MCP tools work correctly via Claude
- [ ] Audio messages still work (ffmpeg + send)
- [ ] Media download works

### 8. Cleanup

Once everything works:
- Remove `whatsapp-bridge/` directory (the custom Go bridge)
- Remove `baileys-bridge/` directory (legacy, already unused)
- Update `CLAUDE.md` to reflect new architecture
- Update `README.md`

### 9. Data migration

The existing SQLite database (`whatsapp-bridge/store/messages.db`) has historical messages. wacli uses its own database in `~/.wacli/`. Options:
- Let wacli re-sync history (may take time but cleanest)
- Write a one-time migration script to import old messages (complex, probably not worth it)
- Keep old DB as read-only archive

Recommendation: Let wacli re-sync. Run `wa follow` for a while to build up the message database.

## Files to modify

- `~/nixos-config/pkgs/wacli.nix` — NEW: Nix package
- `~/nixos-config/modules/core/packages.nix` — ADD: wacli package reference
- `whatsapp-mcp-server/whatsapp.py` — REWRITE: subprocess calls instead of HTTP/SQLite
- `whatsapp-mcp-server/main.py` — MINOR: remove bridge health check, update tool descriptions
- `whatsapp-mcp-server/audio.py` — MINOR: change send step only
- `CLAUDE.md` — UPDATE: architecture description
- `README.md` — UPDATE: installation instructions

## Files to delete

- `whatsapp-bridge/` — entire directory (custom Go bridge)
- `baileys-bridge/` — entire directory (legacy Node.js bridge)
- `sync_all_history.py` — no longer needed (wacli handles this)

## Constraints

- DO NOT run `nixos-rebuild` or `./rebuild-nixos` — tell the user to do it
- Test each step incrementally
- Keep the old bridge running until wacli is fully verified
- The Python MCP server must maintain the same tool interface (tool names, parameters) so Claude integrations don't break
