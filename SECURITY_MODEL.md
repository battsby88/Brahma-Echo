# Brahma Echo — Threat Model

_Scope: `battsby88/Brahma-Echo`. Builds on the repository's own `SECURITY.md` ("Brahma Echo Security Overview"). No infrastructure repository: Brahma Echo is a Windows desktop app that runs on the user's own PC, with no cloud deployment._

## 1. System overview and trust boundaries

Brahma Echo is a single-user, voice- and text-driven desktop assistant (`main.py`, `ui.py`). It runs with the user's own Windows privileges. A Gemini model (OpenRouter fallback, `llm_client.py`, `or_client.py`) picks tool calls, and `main.py::_execute_tool` dispatches them to the `actions/*` modules. Those modules can run shell commands, drive the mouse and keyboard, and read and write files.

Trust boundaries:
1. **Network → PC.** Two LAN-facing servers bind to `0.0.0.0`: the Dashboard (`dashboard/server.py`, HTTP :8000, legacy HTTPS alias :8001) and the Brahma Connect gateway (`brahma_connect/gateway/server.py`, HTTP/WS :8765, mDNS advertised).
2. **Discord → PC.** `discord_bot.py` forwards DMs and @mentions to the assistant through `_app_submitter`.
3. **Untrusted content → LLM → tools.** Web pages, emails, files, clipboard text, screen OCR and Instagram DMs reach the model, and the model's tool calls run with the user's privileges.
4. **PC → paired Android phone.** `brahma-connect-android` runs commands sent by the gateway (`DeviceCommandHandler.kt`): file read/write/delete, UI tap/type through an accessibility service, unlock with a PIN.
5. **Update source → PC code.** `updater.py` / `core/updater.py` fetch from `github.com/titechprabhasolutions/Brahma---personal` (`git reset --hard origin/main` then restart). The auto-heal engine (`actions/auto_heal_engine.py`) writes LLM-generated patches into the source tree.

## 2. Components

| Component | Code |
|---|---|
| **Desktop Agent** | `main.py`, `ui.py`, `agent/`, `core/`, `actions/` (except those listed below), `plugin_manager.py`, `plugins/`, `memory/`, `workspace_store.py`, `smart_home*`, `llm_client.py`, `or_client.py` |
| **Dashboard** | `dashboard/` (FastAPI server, `app.html`, `login.html`) |
| **Brahma Connect Gateway** | `brahma_connect/`, `actions/brahma_connect.py`, `config/brahma_connect*` |
| **Android Companion** | `brahma-connect-android/` |
| **Discord Bot** | `discord_bot.py` |
| **Self-Update & Auto-Heal** | `updater.py`, `core/updater.py`, `core/boot_sentry.py`, `actions/auto_heal_engine.py`, `actions/brahma_dev_agent.py`, `actions/claude_code_bridge.py`, `bootstrap.ps1`, `start_brahma.*` |

## 3. Entry points and who can reach them

- **Dashboard :8000/:8001.** Anyone on the LAN can reach it (`_ensure_network_access` opens the firewall). Logging in needs a 6-character one-time key (`new_key`, 10-minute expiry) shown in the desktop UI or as a QR code (`/auto-login?key=`). A successful login issues an in-memory bearer token. `/api/command` and `/ws` put arbitrary text into the assistant's command queue, which has the same power as the local user speaking. A persistent `device_token` (`/api/device-login`) re-issues tokens and lasts until `/api/revoke-devices`. Uploads are written to the user-data uploads dir.
- **Gateway :8765.** Anyone on the LAN can reach it. Per SECURITY.md, the REST admin routes (`/gateway/pair`, `/gateway/devices`, `/gateway/pending/*/approve`, `/revoke`, `/forget`, `/gateway/logs`) have **no authentication**. On WS `/ws`, `HELLO` creates a pending request, and `PAIR_REQUEST` with a valid pairing token or 6-digit code creates a device and returns a `device_secret`. `AUTHENTICATE` checks the secret's SHA-256 hash in constant time. `CHAT_MESSAGE` and `RESULT` frames are handled per connection.
- **Discord.** Anyone who can DM the bot or @mention it in a shared server. There is no allow-list of Discord users. `target_channel_id` only filters guild messages.
- **Indirect input.** Browser automation (`actions/browser_control.py`, `playwright_mcp_client.py`), web search, email and Google Workspace (`google_workspace_mcp.py`), Instagram (`instagram_chat.py`, `instagram_mcp.py`), clipboard (`core/clipboard_sentry.py`), screen OCR (`screen_processor.py`), and documents and uploads (`file_processor.py`).
- **Local filesystem.** `config/` and the user-data dir (`core/user_paths.py`): API keys, device registry, learned rules (injected into the system prompt), and `plugins/*.py` (loaded with `exec_module`).

## 4. Assets and sensitivity

- **Control of the user's Windows PC:** shell (`brahma_dev_agent.bash`, PowerShell), input injection, file operations, shutdown. The highest-impact asset.
- **The paired Android phone:** files, UI control, unlock PIN (`device_pins` in settings).
- **Credentials** (plaintext in `config/api_keys.json`, `discord_bot.json`, Instagram/Google sessions): Gemini/OpenRouter keys, Discord bot token, Google OAuth, Instagram session.
- **Personal data:** long-term memory graph (`memory/long_term.json`), chats, calendar, nutrition logs, uploads, screenshots and audio.
- **Integrity of the app's own source:** updater, auto-heal patches, plugins, learned rules.

## 5. Attacker profiles (user: all of them matter)

1. **LAN attacker** on the same Wi-Fi: reaches the Dashboard and gateway directly and can sniff plaintext WS traffic.
2. **Discord user** who can DM or mention the bot.
3. **Malicious content author** (web page, email, document, Instagram DM) who uses prompt injection to make the model call dangerous tools.
4. **Supply chain / update source:** compromise of the upstream GitHub repo or a dependency.
5. **Other local OS user:** reads plaintext config, or plants a plugin or learned rule.

## 6. Existing controls

- Dashboard: one-time 6-character keys with expiry, `secrets` RNG, 32-byte bearer tokens, AES-256-CBC command encryption with a key derived from the one-time key, filename sanitisation and a size cap on uploads, `Path.name` stripping on downloads.
- Gateway: pairing offers expire after 300 s, explicit user approval of pending requests, 48-byte device secrets stored as SHA-256 hashes, `hmac.compare_digest`, revocation.
- `core/confirm.py`: confirmation of irreversible actions through a UI banner the model cannot forge. `core/undo.py` for reversible ones.
- Auto-heal: `PROTECTED_CORE_FILES`, AST/`py_compile` check, `.bak` backups, `boot_sentry` rollback.
- Updater: fast-forward only and only on a clean tree (`updater.py`); `core/updater.py` does a hard reset.
- Secrets files are listed in `.gitignore`.

## 7. Out of scope / accepted risk (per user)

- **Nothing is ruled out.** The user said all five attacker profiles matter and all assets above matter equally.
- **LAN exposure is NOT accepted risk.** The SECURITY.md limitations (no gateway TLS, unauthenticated gateway admin REST routes, `0.0.0.0` bind, plaintext WS, plaintext API key storage) are in scope and should be fixed, even though SECURITY.md documents them.

## 8. Open questions

- Is the Discord bot meant to be used only by its owner? (The code has no allow-list of users.)
