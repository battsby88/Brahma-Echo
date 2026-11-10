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


class BlenderMCPClient:
    """Client for Blender MCP server (cli-anything-blender or blender-mcp)."""

    def __init__(self, server_name: str = "blender"):
        self.server_name = server_name
        self._session: Optional[ClientSession] = None
        self._tools: List[Dict] = []

    async def start(self) -> bool:
        if not MCP_AVAILABLE:
            _log("[BlenderMCP] MCP package not available. Install with: pip install mcp")
            return False

        try:
            cmd = "cli-anything-blender" if self.server_name == "blender" else "blender-mcp"
            if not shutil.which(cmd):
                _log(f"[BlenderMCP] {cmd} not found in PATH")
                return False

            server_params = StdioServerParameters(command=cmd, args=[])

            read_stream, write_stream = await stdio_client(server_params).__aenter__()
            self._session = ClientSession(read_stream, write_stream)
            await self._session.__aenter__()

            init_result = await self._session.initialize()
            _log(f"[BlenderMCP] Initialized: {init_result}")

            tools_result = await self._session.list_tools()
            self._tools = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools_result.tools]
            _log(f"[BlenderMCP] Available tools: {[t['name'] for t in self._tools]}")
            return True

        except Exception as e:
            _log(f"[BlenderMCP] Failed to start: {e}")
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


_blender_client: Optional[BlenderMCPClient] = None


async def _get_blender_client() -> BlenderMCPClient:
    global _blender_client
    if _blender_client is None:
        _blender_client = BlenderMCPClient("blender")
        await _blender_client.start()
    return _blender_client


def blender_scene_new() -> Dict:
    """Create a new Blender scene."""
    return _run_async(_blender_scene_new_async())


async def _blender_scene_new_async() -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("scene_new", {})


def blender_scene_open(path: str) -> Dict:
    """Open an existing Blender scene file."""
    return _run_async(_blender_scene_open_async(path))


async def _blender_scene_open_async(path: str) -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("scene_open", {"path": path})


def blender_scene_save(path: str) -> Dict:
    """Save the current Blender scene."""
    return _run_async(_blender_scene_save_async(path))


async def _blender_scene_save_async(path: str) -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("scene_save", {"path": path})


def blender_object_add(object_type: str = "CUBE", name: str = "", location: List[float] = None, rotation: List[float] = None, scale: List[float] = None) -> Dict:
    """Add a primitive object to the scene. Types: CUBE, SPHERE, CYLINDER, CONE, TORUS, PLANE, MONKEY."""
    return _run_async(_blender_object_add_async(object_type, name, location, rotation, scale))


async def _blender_object_add_async(object_type: str, name: str, location: List[float], rotation: List[float], scale: List[float]) -> Dict:
    client = await _get_blender_client()
    args = {"type": object_type.upper()}
    if name:
        args["name"] = name
    if location:
        args["location"] = location
    if rotation:
        args["rotation"] = rotation
    if scale:
        args["scale"] = scale
    return await client.call_tool("object_add", args)


def blender_object_remove(name: str) -> Dict:
    """Remove an object by name."""
    return _run_async(_blender_object_remove_async(name))


async def _blender_object_remove_async(name: str) -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("object_remove", {"name": name})


def blender_object_transform(name: str, location: List[float] = None, rotation: List[float] = None, scale: List[float] = None) -> Dict:
    """Transform an object (move, rotate, scale)."""
    return _run_async(_blender_object_transform_async(name, location, rotation, scale))


async def _blender_object_transform_async(name: str, location: List[float], rotation: List[float], scale: List[float]) -> Dict:
    client = await _get_blender_client()
    args = {"name": name}
    if location:
        args["location"] = location
    if rotation:
        args["rotation"] = rotation
    if scale:
        args["scale"] = scale
    return await client.call_tool("object_transform", args)


def blender_material_create(name: str, color: List[float] = None, metallic: float = 0.0, roughness: float = 0.5) -> Dict:
    """Create a new material."""
    return _run_async(_blender_material_create_async(name, color, metallic, roughness))


async def _blender_material_create_async(name: str, color: List[float], metallic: float, roughness: float) -> Dict:
    client = await _get_blender_client()
    args = {"name": name}
    if color:
        args["color"] = color
    args["metallic"] = metallic
    args["roughness"] = roughness
    return await client.call_tool("material_create", args)


def blender_material_assign(object_name: str, material_name: str) -> Dict:
    """Assign a material to an object."""
    return _run_async(_blender_material_assign_async(object_name, material_name))


async def _blender_material_assign_async(object_name: str, material_name: str) -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("material_assign", {"object": object_name, "material": material_name})


def blender_render(engine: str = "CYCLES", output_path: str = "", samples: int = 128, resolution: List[int] = None) -> Dict:
    """Render the scene. Engines: CYCLES, EEVEE, WORKBENCH."""
    return _run_async(_blender_render_async(engine, output_path, samples, resolution))


async def _blender_render_async(engine: str, output_path: str, samples: int, resolution: List[int]) -> Dict:
    client = await _get_blender_client()
    args = {"engine": engine.upper()}
    if output_path:
        args["output_path"] = output_path
    args["samples"] = samples
    if resolution:
        args["resolution"] = resolution
    return await client.call_tool("render", args)


def blender_python_execute(code: str) -> Dict:
    """Execute arbitrary Python code in Blender (bpy)."""
    return _run_async(_blender_python_execute_async(code))


async def _blender_python_execute_async(code: str) -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("execute_python", {"code": code})


def blender_list_objects() -> Dict:
    """List all objects in the scene."""
    return _run_async(_blender_list_objects_async())


async def _blender_list_objects_async() -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("list_objects", {})


def blender_get_object_info(name: str) -> Dict:
    """Get detailed info about an object."""
    return _run_async(_blender_get_object_info_async(name))


async def _blender_get_object_info_async(name: str) -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("get_object_info", {"name": name})


def blender_undo() -> Dict:
    """Undo last operation."""
    return _run_async(_blender_undo_async())


async def _blender_undo_async() -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("undo", {})


def blender_redo() -> Dict:
    """Redo last undone operation."""
    return _run_async(_blender_redo_async())


async def _blender_redo_async() -> Dict:
    client = await _get_blender_client()
    return await client.call_tool("redo", {})


def _run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def blender_control(action: str, **kwargs) -> Dict:
    """
    Unified Blender control entry point.
    
    Actions:
    - scene_new, scene_open, scene_save
    - object_add, object_remove, object_transform, list_objects, get_object_info
    - material_create, material_assign
    - render
    - python_execute
    - undo, redo
    """
    actions = {
        "scene_new": blender_scene_new,
        "scene_open": lambda: blender_scene_open(kwargs.get("path", "")),
        "scene_save": lambda: blender_scene_save(kwargs.get("path", "")),
        "object_add": lambda: blender_object_add(
            kwargs.get("object_type", "CUBE"),
            kwargs.get("name", ""),
            kwargs.get("location"),
            kwargs.get("rotation"),
            kwargs.get("scale")
        ),
        "object_remove": lambda: blender_object_remove(kwargs.get("name", "")),
        "object_transform": lambda: blender_object_transform(
            kwargs.get("name", ""),
            kwargs.get("location"),
            kwargs.get("rotation"),
            kwargs.get("scale")
        ),
        "list_objects": blender_list_objects,
        "get_object_info": lambda: blender_get_object_info(kwargs.get("name", "")),
        "material_create": lambda: blender_material_create(
            kwargs.get("name", ""),
            kwargs.get("color"),
            kwargs.get("metallic", 0.0),
            kwargs.get("roughness", 0.5)
        ),
        "material_assign": lambda: blender_material_assign(kwargs.get("object_name", ""), kwargs.get("material_name", "")),
        "render": lambda: blender_render(
            kwargs.get("engine", "CYCLES"),
            kwargs.get("output_path", ""),
            kwargs.get("samples", 128),
            kwargs.get("resolution")
        ),
        "python_execute": lambda: blender_python_execute(kwargs.get("code", "")),
        "undo": blender_undo,
        "redo": blender_redo,
    }

    if action not in actions:
        return {"error": f"Unknown action: {action}. Available: {list(actions.keys())}"}

    try:
        return actions[action]()
    except Exception as e:
        return {"error": f"Blender control error: {e}"}