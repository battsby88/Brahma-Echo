# Brahma Echo — Local Setup Guide

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/battsby88/Brahma-Echo.git
cd Brahma-Echo

# 2. Run the bootstrap installer (Windows)
# PowerShell (Admin):
.\bootstrap.ps1

# OR Batch:
.\start_brahma.bat

# 3. For manual setup / non-Windows:
pip install -r requirements.txt
playwright install
```

---

## Detailed Installation

### Windows (Recommended)

**Option A: Full Bootstrap (installs Python, Node, deps, creates venv)**
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\bootstrap.ps1
```

**Option B: Manual (if Python already installed)**
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install
```

### Linux/macOS

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install
```

---

## Running Brahma Echo

### GUI Mode (PyQt6)
```bash
# Windows
.\start_brahma.bat

# Linux/macOS
source .venv/bin/activate
python main.py
```

### Web Dashboard (port 8000)
```bash
# Terminal 1: Start dashboard
python -m dashboard.server

# Terminal 2: Start modern UI (port 8080)
cd ui_modern
python -m http.server 8080
# Open http://localhost:8080
```

### Headless / CLI
```bash
# Run specific tools
python -c "from actions.blender_control import blender_control; print(blender_control('scene_new'))"
```

---

## Configuration

### API Keys (First Run)
1. Start Brahma Echo
2. Say "Open settings" or click Settings in UI
3. Add your API keys:
   - **Gemini API Key** (required): Get from [Google AI Studio](https://aistudio.google.com/apikey)
   - **Google Workspace** (optional): OAuth credentials for Gmail/Calendar/Drive
   - **Instagram** (optional): For social features

### 3D/CAD Software (Optional)
For full tool integration, install:
- **Blender** 4.2+: `pip install cli-anything-blender`
- **Cinema 4D** R2024+: Install `cinema4d-mcp` plugin
- **AutoCAD** 2024+: Install `autocad-mcp` (Windows only)

---

## Project Structure

```
Brahma-Echo/
├── main.py                    # Main entry point
├── bootstrap.ps1              # Windows installer
├── start_brahma.bat           # Windows launcher
├── requirements.txt           # Python dependencies
├── config/
│   ├── mcp_servers.json      # MCP server config
│   └── api_keys.json.enc     # Encrypted API keys (auto-generated)
├── actions/                   # 29 tool modules
│   ├── blender_control.py
│   ├── cinema4d_control.py
│   ├── autocad_control.py
│   ├── replica_pipeline.py
│   └── ...
├── core/                      # Core systems
│   ├── secure_keys.py        # Encrypted key management
│   ├── skill_registry.py     # Skill loader (26 skills)
│   └── ...
├── dashboard/
│   └── server.py             # FastAPI + WebSocket
├── ui_modern/                 # Glassmorphism web UI
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── sw.js                 # Service Worker
├── .claude/skills/            # 26 installed skills
│   ├── replica-* (11 skills)
│   ├── cli-anything-blender
│   ├── blender-mcp
│   ├── cinema4d-mcp
│   ├── autocad-mcp-premium
│   └── cad-edit
└── .venv/                     # Virtual environment (created by bootstrap)
```

---

## Key Features

| Category | Capabilities |
|----------|--------------|
| **Voice** | Wake word, barge-in (<50ms), Hinglish support |
| **3D/CAD** | Blender, Cinema 4D, AutoCAD (MCP + headless LT) |
| **App Cloning** | Replica 11-skill pipeline (recon → deploy) |
| **System** | Diagnostics, brightness, process mgmt, battery |
| **Web** | Browser automation, screenshots, scraping |
| **Google** | Gmail, Calendar, Drive (OAuth) |
| **Security** | PBKDF2 100k, Fernet encryption, OS keyring |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Module not found" | Run `pip install -r requirements.txt` in venv |
| "Playwright browsers missing" | Run `playwright install` |
| "Permission denied" (Windows) | Run PowerShell as Admin |
| "Port 8000 in use" | Kill existing: `taskkill /F /IM python.exe` |
| WebSocket connection failed | Ensure dashboard.server is running on port 8000 |
| API key errors | Check Settings → API Keys in UI |

---

## Security Notes

- **API keys** encrypted with Fernet (AES-256) + OS keyring
- **Local-first** — no cloud dependency for core features
- **PIN auth** — 8-char, rate-limited (10/min)
- **CSP/HSTS** headers on dashboard
- **WebSocket auth** via `Authorization: Bearer` header

---

## Updating

```bash
git pull origin main
pip install -r requirements.txt
playwright install
```

---

## License

MIT License — see LICENSE file for details.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/battsby88/Brahma-Echo/issues)
- **Docs**: See `docs/` folder (if present)
- **Logs**: `FATAL_CRASH.log` for crashes, console for runtime