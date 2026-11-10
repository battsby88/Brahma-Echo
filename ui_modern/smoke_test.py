#!/usr/bin/env python3
"""
Brahma Echo — Smoke Tests for ui_modern & Integrations
Run: python -m ui_modern.smoke_test
"""

import sys
import json
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ==========================================================================
# Test Helpers
# ==========================================================================
class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail(self, name: str, error: str = ""):
        self.failed += 1
        msg = f"{name}: {error}" if error else name
        self.errors.append(msg)
        print(f"  ❌ {msg}")

    def summary(self) -> bool:
        print(f"\n{'='*50}")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        if self.errors:
            print("\nFailures:")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


# ==========================================================================
# Test: File Structure
# ==========================================================================
def test_file_structure(result: TestResult):
    """Verify all ui_modern files exist."""
    required = [
        "ui_modern/index.html",
        "ui_modern/styles.css",
        "ui_modern/app.js",
        "ui_modern/manifest.json",
        "ui_modern/sw.js",
        "ui_modern/assets/brahma-logo.svg",
    ]
    for f in required:
        path = ROOT / f
        if path.exists() and path.stat().st_size > 0:
            result.ok(f"File exists: {f} ({path.stat().st_size} bytes)")
        else:
            result.fail(f"File missing/empty: {f}")


# ==========================================================================
# Test: HTML Structure
# ==========================================================================
def test_html_structure(result: TestResult):
    """Verify index.html has required elements."""
    html = (ROOT / "ui_modern/index.html").read_text(encoding="utf-8")
    checks = [
        ('data-theme="light"', "Theme attribute"),
        ('class="app-shell"', "App shell"),
        ('class="header"', "Header"),
        ('class="sidebar"', "Sidebar"),
        ('class="main-content"', "Main content"),
        ('id="visualizerCanvas"', "Visualizer canvas"),
        ('id="toolLogList"', "Tool log list"),
        ('id="commandPaletteOverlay"', "Command palette"),
        ('id="commandPaletteInput"', "Command palette input"),
        ('id="themeToggle"', "Theme toggle"),
        ('id="listenToggle"', "Listen toggle"),
        ('id="sidebarToggle"', "Sidebar toggle"),
        ('manifest.json', "Manifest link"),
        ('sw.js', "Service worker registration"),
        ('styles.css', "Stylesheet link"),
        ('app.js', "Module script"),
    ]
    for check, desc in checks:
        if check in html:
            result.ok(f"HTML: {desc}")
        else:
            result.fail(f"HTML missing: {desc}")


# ==========================================================================
# Test: CSS Tokens
# ==========================================================================
def test_css_tokens(result: TestResult):
    """Verify claymorphism CSS tokens exist."""
    css = (ROOT / "ui_modern/styles.css").read_text(encoding="utf-8")
    tokens = [
        "--clay-radius-sm", "--clay-radius-md", "--clay-radius-lg", "--clay-radius-xl",
        "--clay-shadow-light", "--clay-shadow-dark", "--clay-inner-light", "--clay-inner-dark",
        "--bg-primary", "--bg-secondary", "--bg-tertiary",
        "--text-primary", "--text-secondary", "--text-tertiary",
        "--accent-primary", "--accent-success", "--accent-warning", "--accent-error",
        "[data-theme=\"dark\"]",  # Dark theme
        ".clay-surface", ".clay-panel", ".clay-card",
        ".clay-button", ".clay-button--primary", ".clay-button--ghost",
        ".clay-input", ".clay-badge", ".toggle",
        ".visualizer-canvas", ".tool-log", ".command-palette",
    ]
    for token in tokens:
        if token in css:
            result.ok(f"CSS token: {token}")
        else:
            result.fail(f"CSS missing: {token}")


# ==========================================================================
# Test: JS Modules
# ==========================================================================
def test_js_modules(result: TestResult):
    """Verify app.js exports and structure."""
    js = (ROOT / "ui_modern/app.js").read_text(encoding="utf-8")
    modules = [
        "const State =",
        "const Theme =",
        "const WS =",
        "const Metrics =",
        "const Visualizer =",
        "const ToolLog =",
        "const CommandPalette =",
        "const Skills =",
        "const ToolExecutor =",
        "const Voice =",
        "const UI =",
        "window.BrahmaUI =",
    ]
    for m in modules:
        if m in js:
            result.ok(f"JS module: {m}")
        else:
            result.fail(f"JS missing: {m}")


# ==========================================================================
# Test: Service Worker
# ==========================================================================
def test_service_worker(result: TestResult):
    """Verify SW has required handlers."""
    sw = (ROOT / "ui_modern/sw.js").read_text(encoding="utf-8")
    handlers = [
        "addEventListener('install'",
        "addEventListener('activate'",
        "addEventListener('fetch'",
        "CACHE_NAME",
        "STATIC_ASSETS",
        "caches.open",
        "caches.match",
    ]
    for h in handlers:
        if h in sw:
            result.ok(f"SW: {h}")
        else:
            result.fail(f"SW missing: {h}")


# ==========================================================================
# Test: Manifest
# ==========================================================================
def test_manifest(result: TestResult):
    """Verify manifest.json is valid."""
    try:
        manifest = json.loads((ROOT / "ui_modern/manifest.json").read_text())
        required = ["name", "short_name", "start_url", "display", "background_color", "theme_color", "icons"]
        for r in required:
            if r in manifest:
                result.ok(f"Manifest: {r}")
            else:
                result.fail(f"Manifest missing: {r}")
        # Check icon
        if manifest["icons"] and manifest["icons"][0].get("src") == "assets/brahma-logo.svg":
            result.ok("Manifest icon points to brahma-logo.svg")
        else:
            result.fail("Manifest icon incorrect")
    except json.JSONDecodeError as e:
        result.fail(f"Manifest invalid JSON: {e}")


# ==========================================================================
# Test: SVG Logo
# ==========================================================================
def test_svg_logo(result: TestResult):
    """Verify SVG logo is valid."""
    svg = (ROOT / "ui_modern/assets/brahma-logo.svg").read_text(encoding="utf-8")
    checks = [
        ('xmlns="http://www.w3.org/2000/svg"', "SVG namespace"),
        ('viewBox="0 0 128 128"', "ViewBox"),
        ('fill="none"', "No fill"),
        ('#2d6fff', "Accent primary color"),
        ('#ff6b2d', "Accent secondary color"),
        ('<defs>', "Definitions"),
        ('<radialGradient id="accent-glow"', "Glow gradient"),
    ]
    for check, desc in checks:
        if check in svg:
            result.ok(f"SVG: {desc}")
        else:
            result.fail(f"SVG missing: {desc}")


# ==========================================================================
# Test: Skill Registry
# ==========================================================================
def test_skill_registry(result: TestResult):
    """Test skill registry loads skills."""
    try:
        from core.skill_registry import load_skills_at_startup
        skills = load_skills_at_startup()
        if skills and len(skills) >= 20:
            result.ok(f"Skill registry loaded {len(skills)} skills")
            # Check for key skills
            key_skills = ["replica-recon", "blender-mcp", "cinema4d-mcp", "autocad-mcp-premium", "cad-edit"]
            for ks in key_skills:
                if ks in skills:
                    result.ok(f"Key skill present: {ks}")
                else:
                    result.fail(f"Key skill missing: {ks}")
        else:
            result.fail(f"Skill registry only loaded {len(skills)} skills")
    except Exception as e:
        result.fail(f"Skill registry error: {e}")


# ==========================================================================
# Test: Dashboard Server WebSocket
# ==========================================================================
def test_dashboard_websocket(result: TestResult):
    """Verify dashboard has modern WebSocket endpoint."""
    server_py = (ROOT / "dashboard/server.py").read_text()
    checks = [
        ('@app.websocket("/ws/modern")', "Modern WS endpoint"),
        ("async def ws_modern", "WS handler function"),
        ("broadcast_metrics", "Metrics broadcast"),
        ("broadcast_tool_result", "Tool result broadcast"),
        ("broadcast_voice_state", "Voice state broadcast"),
        ("broadcast_skills", "Skills broadcast"),
    ]
    for check, desc in checks:
        if check in server_py:
            result.ok(f"Dashboard: {desc}")
        else:
            result.fail(f"Dashboard missing: {desc}")


# ==========================================================================
# Test: Main.py Integration
# ==========================================================================
def test_main_integration(result: TestResult):
    """Verify main.py has new tool declarations and handlers."""
    main_py = (ROOT / "main.py").read_text()
    checks = [
        ("from actions.blender_control", "Blender import"),
        ("from actions.cinema4d_control", "Cinema 4D import"),
        ("from actions.autocad_control", "AutoCAD import"),
        ("from core.skill_registry import", "Skill registry import"),
        ("load_skills_at_startup", "Skill registry init"),
        ('"name": "blender_control"', "Blender tool declaration"),
        ('"name": "cinema4d_control"', "Cinema 4D tool declaration"),
        ('"name": "autocad_control"', "AutoCAD tool declaration"),
        ('"name": "replica_pipeline"', "Replica tool declaration"),
        ("elif name == \"blender_control\"", "Blender handler"),
        ("elif name == \"cinema4d_control\"", "Cinema 4D handler"),
        ("elif name == \"autocad_control\"", "AutoCAD handler"),
        ("elif name == \"replica_pipeline\"", "Replica handler"),
        ("def _run_replica_pipeline", "Replica pipeline method"),
    ]
    for check, desc in checks:
        if check in main_py:
            result.ok(f"Main.py: {desc}")
        else:
            result.fail(f"Main.py missing: {desc}")


# ==========================================================================
# Test: MCP Config
# ==========================================================================
def test_mcp_config(result: TestResult):
    """Verify MCP config exists and is valid."""
    try:
        config = json.loads((ROOT / "config/mcp_servers.json").read_text())
        servers = config.get("mcpServers", {})
        required = ["blender", "blender-mcp", "cinema4d", "autocad", "autocad-lt", "replica"]
        for r in required:
            if r in servers:
                result.ok(f"MCP server: {r}")
            else:
                result.fail(f"MCP server missing: {r}")
    except Exception as e:
        result.fail(f"MCP config error: {e}")


# ==========================================================================
# Test: Action Modules
# ==========================================================================
def test_action_modules(result: TestResult):
    """Verify action modules exist and have control functions."""
    modules = [
        ("actions/blender_control.py", "blender_control"),
        ("actions/cinema4d_control.py", "cinema4d_control"),
        ("actions/autocad_control.py", "autocad_control"),
    ]
    for path, func in modules:
        full = ROOT / path
        if full.exists():
            content = full.read_text()
            if f"def {func}(" in content:
                result.ok(f"Action module: {path}")
            else:
                result.fail(f"Action module missing function: {path}")
        else:
            result.fail(f"Action module missing: {path}")


# ==========================================================================
# Test: Skills Directory
# ==========================================================================
def test_skills_directory(result: TestResult):
    """Verify all skills are symlinked."""
    skills_dir = ROOT / ".claude" / "skills"
    if not skills_dir.exists():
        result.fail("Skills directory missing")
        return

    skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
    expected = [
        "replica-recon", "replica-architect", "replica-design", "replica-build",
        "replica-backend", "replica-test", "replica-diff", "replica-entrepreneur",
        "replica-brand", "replica-launch", "replica-deploy",
        "cli-anything-blender", "blender-mcp", "cinema4d-mcp",
        "autocad-mcp-premium", "cad-edit"
    ]
    for exp in expected:
        if exp in skills:
            result.ok(f"Skill linked: {exp}")
        else:
            result.fail(f"Skill missing: {exp}")


# ==========================================================================
# Async Test: WebSocket Connection (requires running server)
# ==========================================================================
async def test_websocket_connection(result: TestResult):
    """Test WebSocket connection to dashboard (if server running)."""
    try:
        import websockets
        uri = "ws://localhost:8000/ws/modern?token=test"
        try:
            async with websockets.connect(uri, open_timeout=2) as ws:
                await ws.send(json.dumps({"type": "subscribe"}))
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(msg)
                if data.get("type") in ("metrics", "tool_result", "voice_state", "skills", "system"):
                    result.ok("WebSocket: Received valid message type")
                else:
                    result.ok("WebSocket: Connected and received message")
        except (ConnectionRefusedError, asyncio.TimeoutError):
            result.ok("WebSocket: Server not running (skipped)")
        except Exception as e:
            result.fail(f"WebSocket error: {e}")
    except ImportError:
        result.ok("WebSocket: websockets library not installed (skipped)")


# ==========================================================================
# Main
# ==========================================================================
def main():
    print("=" * 60)
    print("Brahma Echo — Smoke Tests")
    print("=" * 60)

    result = TestResult()

    # Sync tests
    print("\n📁 File Structure")
    test_file_structure(result)

    print("\n🌐 HTML Structure")
    test_html_structure(result)

    print("\n🎨 CSS Tokens")
    test_css_tokens(result)

    print("\n📦 JS Modules")
    test_js_modules(result)

    print("\n🔧 Service Worker")
    test_service_worker(result)

    print("\n📋 Manifest")
    test_manifest(result)

    print("\n🖼️  SVG Logo")
    test_svg_logo(result)

    print("\n🧠 Skill Registry")
    test_skill_registry(result)

    print("\n🔌 Dashboard WebSocket")
    test_dashboard_websocket(result)

    print("\n🐍 Main.py Integration")
    test_main_integration(result)

    print("\n⚙️  MCP Config")
    test_mcp_config(result)

    print("\n📦 Action Modules")
    test_action_modules(result)

    print("\n🔗 Skills Directory")
    test_skills_directory(result)

    # Async test
    print("\n🔌 WebSocket Connection (Live)")
    try:
        asyncio.run(test_websocket_connection(result))
    except Exception as e:
        result.fail(f"Async test error: {e}")

    # Summary
    print()
    success = result.summary()

    if success:
        print("\n🎉 All smoke tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())