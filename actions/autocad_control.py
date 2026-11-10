import asyncio
import json
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def _log(message: str) -> None:
    try:
        print(message.encode("ascii", "replace").decode("ascii"))
    except UnicodeEncodeError:
        print(message.encode("ascii", "replace").decode("ascii"))


class AutoCADMCPClient:
    """Client for AutoCAD MCP server (U-C4N autocad-mcp-pro)."""

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._tools: List[Dict] = []

    async def start(self) -> bool:
        if not MCP_AVAILABLE:
            _log("[AutoCADMCP] MCP package not available. Install with: pip install mcp")
            return False

        try:
            cmd = "autocad-mcp"
            if not shutil.which(cmd):
                _log(f"[AutoCADMCP] {cmd} not found in PATH")
                return False

            env = {
                "AUTOCAD_MCP_BACKEND": "auto",
                "ALLOWED_PATHS": "C:\\Users\\%USERNAME%\\Documents\\AutoCAD",
                "TOOL_PROFILE": "full",
                "TOOL_PACKS": "all",
                "DISCOVERY_MODE": "search"
            }

            server_params = StdioServerParameters(command=cmd, args=[], env=env)

            read_stream, write_stream = await stdio_client(server_params).__aenter__()
            self._session = ClientSession(read_stream, write_stream)
            await self._session.__aenter__()

            init_result = await self._session.initialize()
            _log(f"[AutoCADMCP] Initialized: {init_result}")

            tools_result = await self._session.list_tools()
            self._tools = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools_result.tools]
            _log(f"[AutoCADMCP] Available tools: {len(self._tools)} tools loaded")
            return True

        except Exception as e:
            _log(f"[AutoCADMCP] Failed to start: {e}")
            return False

    async def stop(self):
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None

    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        if not self._session:
            return {"error": "MCP session not started"}
        try:
            result = await self._session.call_tool(tool_name, arguments)
            return {"result": result.content}
        except Exception as e:
            return {"error": str(e)}


_autocad_client: Optional[AutoCADMCPClient] = None


async def _get_autocad_client() -> AutoCADMCPClient:
    global _autocad_client
    if _autocad_client is None:
        _autocad_client = AutoCADMCPClient()
        await _autocad_client.start()
    return _autocad_client


def autocad_ping() -> Dict:
    """Test connection to AutoCAD."""
    return _run_async(_autocad_ping_async())


async def _autocad_ping_async() -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("ping", {})


def autocad_list_tools() -> Dict:
    """List all available AutoCAD MCP tools."""
    return _run_async(_autocad_list_tools_async())


async def _autocad_list_tools_async() -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("acad_list_tools", {})


def autocad_list_skills() -> Dict:
    """List all persistent LISP skills."""
    return _run_async(_autocad_list_skills_async())


async def _autocad_list_skills_async() -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("acad_list_skills", {})


def autocad_open_drawing(path: str) -> Dict:
    """Open a DWG/DXF file."""
    return _run_async(_autocad_open_drawing_async(path))


async def _autocad_open_drawing_async(path: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("drawing_open", {"path": path})


def autocad_save_drawing(path: str = "") -> Dict:
    """Save the current drawing."""
    return _run_async(_autocad_save_drawing_async(path))


async def _autocad_save_drawing_async(path: str) -> Dict:
    client = await _get_autocad_client()
    args = {}
    if path:
        args["path"] = path
    return await client.call_tool("drawing_save", args)


def autocad_get_drawing_info() -> Dict:
    """Get info about the current drawing."""
    return _run_async(_autocad_get_drawing_info_async())


async def _autocad_get_drawing_info_async() -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("drawing_info", {})


def autocad_create_line(start: List[float], end: List[float], layer: str = "0") -> Dict:
    """Create a line entity."""
    return _run_async(_autocad_create_line_async(start, end, layer))


async def _autocad_create_line_async(start: List[float], end: List[float], layer: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_create_line", {"start": start, "end": end, "layer": layer})


def autocad_create_circle(center: List[float], radius: float, layer: str = "0") -> Dict:
    """Create a circle entity."""
    return _run_async(_autocad_create_circle_async(center, radius, layer))


async def _autocad_create_circle_async(center: List[float], radius: float, layer: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_create_circle", {"center": center, "radius": radius, "layer": layer})


def autocad_create_polyline(points: List[List[float]], closed: bool = False, layer: str = "0") -> Dict:
    """Create a polyline (LWPOLYLINE)."""
    return _run_async(_autocad_create_polyline_async(points, closed, layer))


async def _autocad_create_polyline_async(points: List[List[float]], closed: bool, layer: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_create_polyline", {"points": points, "closed": closed, "layer": layer})


def autocad_create_text(text: str, position: List[float], height: float = 2.5, layer: str = "0", style: str = "Standard") -> Dict:
    """Create single-line text (TEXT)."""
    return _run_async(_autocad_create_text_async(text, position, height, layer, style))


async def _autocad_create_text_async(text: str, position: List[float], height: float, layer: str, style: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_create_text", {"text": text, "position": position, "height": height, "layer": layer, "style": style})


def autocad_create_mtext(text: str, position: List[float], width: float, height: float = 2.5, layer: str = "0") -> Dict:
    """Create multi-line text (MTEXT)."""
    return _run_async(_autocad_create_mtext_async(text, position, width, height, layer))


async def _autocad_create_mtext_async(text: str, position: List[float], width: float, height: float, layer: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_create_mtext", {"text": text, "position": position, "width": width, "height": height, "layer": layer})


def autocad_create_dimension(start: List[float], end: List[float], offset: float, layer: str = "0") -> Dict:
    """Create an aligned dimension."""
    return _run_async(_autocad_create_dimension_async(start, end, offset, layer))


async def _autocad_create_dimension_async(start: List[float], end: List[float], offset: float, layer: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_create_dimension", {"start": start, "end": end, "offset": offset, "layer": layer})


def autocad_create_hatch(pattern: str, points: List[List[float]], layer: str = "0", scale: float = 1.0) -> Dict:
    """Create a hatch entity."""
    return _run_async(_autocad_create_hatch_async(pattern, points, layer, scale))


async def _autocad_create_hatch_async(pattern: str, points: List[List[float]], layer: str, scale: float) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_create_hatch", {"pattern": pattern, "points": points, "layer": layer, "scale": scale})


def autocad_create_block(name: str, entities: List[Dict], base_point: List[float] = [0, 0, 0]) -> Dict:
    """Create a block definition."""
    return _run_async(_autocad_create_block_async(name, entities, base_point))


async def _autocad_create_block_async(name: str, entities: List[Dict], base_point: List[float]) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("block_create", {"name": name, "entities": entities, "base_point": base_point})


def autocad_insert_block(name: str, position: List[float], scale: List[float] = [1, 1, 1], rotation: float = 0, layer: str = "0") -> Dict:
    """Insert a block reference."""
    return _run_async(_autocad_insert_block_async(name, position, scale, rotation, layer))


async def _autocad_insert_block_async(name: str, position: List[float], scale: List[float], rotation: float, layer: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("block_insert", {"name": name, "position": position, "scale": scale, "rotation": rotation, "layer": layer})


def autocad_create_layer(name: str, color: int = 7, linetype: str = "Continuous", lineweight: int = -1) -> Dict:
    """Create a new layer."""
    return _run_async(_autocad_create_layer_async(name, color, linetype, lineweight))


async def _autocad_create_layer_async(name: str, color: int, linetype: str, lineweight: int) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("layer_create", {"name": name, "color": color, "linetype": linetype, "lineweight": lineweight})


def autocad_set_layer(name: str, on: bool = True, frozen: bool = False, locked: bool = False) -> Dict:
    """Set layer state."""
    return _run_async(_autocad_set_layer_async(name, on, frozen, locked))


async def _autocad_set_layer_async(name: str, on: bool, frozen: bool, locked: bool) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("layer_set", {"name": name, "on": on, "frozen": frozen, "locked": locked})


def autocad_list_layers() -> Dict:
    """List all layers."""
    return _run_async(_autocad_list_layers_async())


async def _autocad_list_layers_async() -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("layer_list", {})


def autocad_query_entities(query: Dict) -> Dict:
    """Query entities by criteria (type, layer, etc.)."""
    return _run_async(_autocad_query_entities_async(query))


async def _autocad_query_entities_async(query: Dict) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_query", query)


def autocad_modify_entity(handle: str, properties: Dict) -> Dict:
    """Modify entity properties by handle."""
    return _run_async(_autocad_modify_entity_async(handle, properties))


async def _autocad_modify_entity_async(handle: str, properties: Dict) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_modify", {"handle": handle, "properties": properties})


def autocad_delete_entity(handle: str) -> Dict:
    """Delete an entity by handle."""
    return _run_async(_autocad_delete_entity_async(handle))


async def _autocad_delete_entity_async(handle: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("entity_delete", {"handle": handle})


def autocad_execute_lisp(code: str) -> Dict:
    """Execute arbitrary AutoLISP code."""
    return _run_async(_autocad_execute_lisp_async(code))


async def _autocad_execute_lisp_async(code: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("execute_lisp", {"code": code})


def autocad_save_skill(name: str, code: str, description: str) -> Dict:
    """Save a persistent LISP skill."""
    return _run_async(_autocad_save_skill_async(name, code, description))


async def _autocad_save_skill_async(name: str, code: str, description: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("acad_save_skill", {"name": name, "code": code, "description": description})


def autocad_get_skill(name: str) -> Dict:
    """Get a skill by name."""
    return _run_async(_autocad_get_skill_async(name))


async def _autocad_get_skill_async(name: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("acad_get_skill", {"name": name})


def autocad_plot_pdf(output_path: str, layout: str = "Model", paper_size: str = "ISO_A4_(210.00_x_297.00_MM)") -> Dict:
    """Plot to PDF."""
    return _run_async(_autocad_plot_pdf_async(output_path, layout, paper_size))


async def _autocad_plot_pdf_async(output_path: str, layout: str, paper_size: str) -> Dict:
    client = await _get_autocad_client()
    return await client.call_tool("plot_pdf", {"output_path": output_path, "layout": layout, "paper_size": paper_size})


# Headless AutoCAD LT (cad-edit) functions using accoreconsole.exe
def autocad_lt_edit_drawing(dwg_path: str, lisp_code: str) -> Dict:
    """Edit a DWG file headlessly using accoreconsole.exe (AutoCAD LT 2024+)."""
    return _run_async(_autocad_lt_edit_drawing_async(dwg_path, lisp_code))


async def _autocad_lt_edit_drawing_async(dwg_path: str, lisp_code: str) -> Dict:
    try:
        # Find accoreconsole.exe
        accoreconsole_paths = [
            r"C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe",
            r"C:\Program Files\Autodesk\AutoCAD 2024\accoreconsole.exe",
            r"C:\Program Files\Autodesk\AutoCAD 2026\accoreconsole.exe",
        ]
        
        accoreconsole = None
        for p in accoreconsole_paths:
            if Path(p).exists():
                accoreconsole = p
                break
        
        if not accoreconsole:
            return {"error": "accoreconsole.exe not found. Install AutoCAD 2024+ or AutoCAD LT 2024+."}

        # Create temporary LISP file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lsp', delete=False) as f:
            f.write(lisp_code)
            lisp_path = f.name

        # Run accoreconsole
        cmd = [
            accoreconsole,
            "/i", dwg_path,
            "/s", lisp_path,
            "/l", "en-US"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # Clean up
        Path(lisp_path).unlink(missing_ok=True)
        
        if result.returncode != 0:
            return {"error": f"accoreconsole failed: {result.stderr}"}
        
        return {"result": result.stdout}
        
    except Exception as e:
        return {"error": f"AutoCAD LT edit error: {e}"}


def autocad_lt_update_keynote(dwg_path: str, old_keynote: str, new_keynote: str, layout: str = "") -> Dict:
    """Renumber a keynote in a drawing."""
    lisp = f"""
(defun c:updatekeynote (/ ss i ent data)
  (setq ss (ssget "X" '((0 . "MTEXT") (1 . "*{old_keynote}*"))))
  (if ss
    (progn
      (repeat (setq i (sslength ss))
        (setq ent (ssname ss (setq i (1- i))))
        (setq data (entget ent))
        (setq data (subst (cons 1 (vl-string-subst "{new_keynote}" "{old_keynote}" (cdr (assoc 1 data)))) (assoc 1 data) data))
        (entmod data)
      )
      (princ (strcat "Updated " (itoa (sslength ss)) " keynotes"))
    )
    (princ "No matching keynotes found")
  )
  (princ)
)
(updatekeynote)
""".format(old_keynote=old_keynote, new_keynote=new_keynote)
    
    return autocad_lt_edit_drawing(dwg_path, lisp)


def autocad_lt_add_revision_cloud(dwg_path: str, points: List[List[float]], layer: str = "REVISION") -> Dict:
    """Add a revision cloud to a drawing."""
    points_str = " ".join([f"{p[0]} {p[1]} {p[2] if len(p) > 2 else 0.0}" for p in points])
    lisp = f"""
(defun c:addrevcloud (/ pts)
  (setq pts '({points_str}))
  (command "_.REVCLOUD" "_ArcLength" 10 "_Rectangular" (car pts) (cadr pts) "")
  (if (tblsearch "LAYER" "{layer}")
    (command "_CHPROP" "_Last" "" "_LA" "{layer}" "")
    (progn
      (command "_LAYER" "_M" "{layer}" "_C" 1 "" "")
      (command "_CHPROP" "_Last" "" "_LA" "{layer}" "")
    )
  )
  (princ "Revision cloud added")
  (princ)
)
(addrevcloud)
"""
    return autocad_lt_edit_drawing(dwg_path, lisp)


def _run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def autocad_control(action: str, **kwargs) -> Dict:
    """
    Unified AutoCAD control entry point (U-C4N MCP Pro + LT headless).
    
    MCP Actions (require AutoCAD running):
    - ping, list_tools, list_skills
    - open_drawing, save_drawing, get_drawing_info
    - create_line, create_circle, create_polyline, create_text, create_mtext, create_dimension, create_hatch
    - create_block, insert_block
    - create_layer, set_layer, list_layers
    - query_entities, modify_entity, delete_entity
    - execute_lisp
    - save_skill, get_skill
    - plot_pdf
    
    LT Headless Actions (work without AutoCAD window, AutoCAD LT 2024+):
    - lt_edit_drawing, lt_update_keynote, lt_add_revision_cloud
    """
    actions = {
        # MCP Pro
        "ping": autocad_ping,
        "list_tools": autocad_list_tools,
        "list_skills": autocad_list_skills,
        "open_drawing": lambda: autocad_open_drawing(kwargs.get("path", "")),
        "save_drawing": lambda: autocad_save_drawing(kwargs.get("path", "")),
        "get_drawing_info": autocad_get_drawing_info,
        "create_line": lambda: autocad_create_line(kwargs.get("start", [0,0,0]), kwargs.get("end", [0,0,0]), kwargs.get("layer", "0")),
        "create_circle": lambda: autocad_create_circle(kwargs.get("center", [0,0,0]), kwargs.get("radius", 1.0), kwargs.get("layer", "0")),
        "create_polyline": lambda: autocad_create_polyline(kwargs.get("points", []), kwargs.get("closed", False), kwargs.get("layer", "0")),
        "create_text": lambda: autocad_create_text(kwargs.get("text", ""), kwargs.get("position", [0,0,0]), kwargs.get("height", 2.5), kwargs.get("layer", "0"), kwargs.get("style", "Standard")),
        "create_mtext": lambda: autocad_create_mtext(kwargs.get("text", ""), kwargs.get("position", [0,0,0]), kwargs.get("width", 100), kwargs.get("height", 2.5), kwargs.get("layer", "0")),
        "create_dimension": lambda: autocad_create_dimension(kwargs.get("start", [0,0,0]), kwargs.get("end", [0,0,0]), kwargs.get("offset", 10), kwargs.get("layer", "0")),
        "create_hatch": lambda: autocad_create_hatch(kwargs.get("pattern", "SOLID"), kwargs.get("points", []), kwargs.get("layer", "0"), kwargs.get("scale", 1.0)),
        "create_block": lambda: autocad_create_block(kwargs.get("name", ""), kwargs.get("entities", []), kwargs.get("base_point", [0,0,0])),
        "insert_block": lambda: autocad_insert_block(kwargs.get("name", ""), kwargs.get("position", [0,0,0]), kwargs.get("scale", [1,1,1]), kwargs.get("rotation", 0), kwargs.get("layer", "0")),
        "create_layer": lambda: autocad_create_layer(kwargs.get("name", ""), kwargs.get("color", 7), kwargs.get("linetype", "Continuous"), kwargs.get("lineweight", -1)),
        "set_layer": lambda: autocad_set_layer(kwargs.get("name", ""), kwargs.get("on", True), kwargs.get("frozen", False), kwargs.get("locked", False)),
        "list_layers": autocad_list_layers,
        "query_entities": lambda: autocad_query_entities(kwargs.get("query", {})),
        "modify_entity": lambda: autocad_modify_entity(kwargs.get("handle", ""), kwargs.get("properties", {})),
        "delete_entity": lambda: autocad_delete_entity(kwargs.get("handle", "")),
        "execute_lisp": lambda: autocad_execute_lisp(kwargs.get("code", "")),
        "save_skill": lambda: autocad_save_skill(kwargs.get("name", ""), kwargs.get("code", ""), kwargs.get("description", "")),
        "get_skill": lambda: autocad_get_skill(kwargs.get("name", "")),
        "plot_pdf": lambda: autocad_plot_pdf(kwargs.get("output_path", ""), kwargs.get("layout", "Model"), kwargs.get("paper_size", "ISO_A4_(210.00_x_297.00_MM)")),
        
        # LT Headless
        "lt_edit_drawing": lambda: autocad_lt_edit_drawing(kwargs.get("dwg_path", ""), kwargs.get("lisp_code", "")),
        "lt_update_keynote": lambda: autocad_lt_update_keynote(kwargs.get("dwg_path", ""), kwargs.get("old_keynote", ""), kwargs.get("new_keynote", ""), kwargs.get("layout", "")),
        "lt_add_revision_cloud": lambda: autocad_lt_add_revision_cloud(kwargs.get("dwg_path", ""), kwargs.get("points", []), kwargs.get("layer", "REVISION")),
    }

    if action not in actions:
        return {"error": f"Unknown action: {action}. Available: {list(actions.keys())}"}

    try:
        return actions[action]()
    except Exception as e:
        return {"error": f"AutoCAD control error: {e}"}