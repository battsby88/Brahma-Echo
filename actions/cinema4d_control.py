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


class Cinema4DMCPClient:
    """Client for Cinema 4D MCP server (cinema4d-mcp from vladmdgolam)."""

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._tools: List[Dict] = []

    async def start(self) -> bool:
        if not MCP_AVAILABLE:
            _log("[Cinema4DMCP] MCP package not available. Install with: pip install mcp")
            return False

        try:
            cmd = "cinema4d-mcp"
            if not shutil.which(cmd):
                _log(f"[Cinema4DMCP] {cmd} not found in PATH")
                return False

            server_params = StdioServerParameters(command=cmd, args=[])

            read_stream, write_stream = await stdio_client(server_params).__aenter__()
            self._session = ClientSession(read_stream, write_stream)
            await self._session.__aenter__()

            init_result = await self._session.initialize()
            _log(f"[Cinema4DMCP] Initialized: {init_result}")

            tools_result = await self._session.list_tools()
            self._tools = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tools_result.tools]
            _log(f"[Cinema4DMCP] Available tools: {[t['name'] for t in self._tools]}")
            return True

        except Exception as e:
            _log(f"[Cinema4DMCP] Failed to start: {e}")
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


_c4d_client: Optional[Cinema4DMCPClient] = None


async def _get_c4d_client() -> Cinema4DMCPClient:
    global _c4d_client
    if _c4d_client is None:
        _c4d_client = Cinema4DMCPClient()
        await _c4d_client.start()
    return _c4d_client


def cinema4d_ping() -> Dict:
    """Test connection to Cinema 4D."""
    return _run_async(_cinema4d_ping_async())


async def _cinema4d_ping_async() -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("ping", {})


def cinema4d_get_scene_info() -> Dict:
    """Get summary info about the active Cinema 4D scene."""
    return _run_async(_cinema4d_get_scene_info_async())


async def _cinema4d_get_scene_info_async() -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("get_scene_info", {})


def cinema4d_list_objects() -> Dict:
    """List all scene objects with hierarchy."""
    return _run_async(_cinema4d_list_objects_async())


async def _cinema4d_list_objects_async() -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("list_objects", {})


def cinema4d_get_object_info(name: str) -> Dict:
    """Get detailed info about an object."""
    return _run_async(_cinema4d_get_object_info_async(name))


async def _cinema4d_get_object_info_async(name: str) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("get_object_info", {"name": name})


def cinema4d_add_primitive(primitive_type: str = "cube", name: str = "", position: List[float] = None, rotation: List[float] = None, scale: List[float] = None) -> Dict:
    """Add a primitive object. Types: cube, sphere, cone, cylinder, torus, plane, disc, pyramid, platonic, tube, oil_tank, capsule."""
    return _run_async(_cinema4d_add_primitive_async(primitive_type, name, position, rotation, scale))


async def _cinema4d_add_primitive_async(primitive_type: str, name: str, position: List[float], rotation: List[float], scale: List[float]) -> Dict:
    client = await _get_c4d_client()
    args = {"type": primitive_type.lower()}
    if name:
        args["name"] = name
    if position:
        args["position"] = position
    if rotation:
        args["rotation"] = rotation
    if scale:
        args["scale"] = scale
    return await client.call_tool("add_primitive", args)


def cinema4d_modify_object(name: str, position: List[float] = None, rotation: List[float] = None, scale: List[float] = None, visible: bool = None) -> Dict:
    """Modify an object's transform or visibility."""
    return _run_async(_cinema4d_modify_object_async(name, position, rotation, scale, visible))


async def _cinema4d_modify_object_async(name: str, position: List[float], rotation: List[float], scale: List[float], visible: bool) -> Dict:
    client = await _get_c4d_client()
    args = {"name": name}
    if position:
        args["position"] = position
    if rotation:
        args["rotation"] = rotation
    if scale:
        args["scale"] = scale
    if visible is not None:
        args["visible"] = visible
    return await client.call_tool("modify_object", args)


def cinema4d_delete_object(name: str) -> Dict:
    """Delete an object by name."""
    return _run_async(_cinema4d_delete_object_async(name))


async def _cinema4d_delete_object_async(name: str) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("delete_object", {"name": name})


def cinema4d_group_objects(names: List[str], group_name: str = "") -> Dict:
    """Group selected objects under a new null."""
    return _run_async(_cinema4d_group_objects_async(names, group_name))


async def _cinema4d_group_objects_async(names: List[str], group_name: str) -> Dict:
    client = await _get_c4d_client()
    args = {"names": names}
    if group_name:
        args["group_name"] = group_name
    return await client.call_tool("group_objects", args)


def cinema4d_set_keyframe(name: str, property_name: str, frame: int, value: Any) -> Dict:
    """Set a keyframe on an object's property (position, rotation, scale, etc.)."""
    return _run_async(_cinema4d_set_keyframe_async(name, property_name, frame, value))


async def _cinema4d_set_keyframe_async(name: str, property_name: str, frame: int, value: Any) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("set_keyframe", {"name": name, "property": property_name, "frame": frame, "value": value})


def cinema4d_create_material(name: str, color: List[float] = None, roughness: float = 0.5, metallic: float = 0.0, emission: List[float] = None) -> Dict:
    """Create a standard material."""
    return _run_async(_cinema4d_create_material_async(name, color, roughness, metallic, emission))


async def _cinema4d_create_material_async(name: str, color: List[float], roughness: float, metallic: float, emission: List[float]) -> Dict:
    client = await _get_c4d_client()
    args = {"name": name}
    if color:
        args["color"] = color
    args["roughness"] = roughness
    args["metallic"] = metallic
    if emission:
        args["emission"] = emission
    return await client.call_tool("create_material", args)


def cinema4d_assign_material(object_name: str, material_name: str) -> Dict:
    """Assign a material to an object."""
    return _run_async(_cinema4d_assign_material_async(object_name, material_name))


async def _cinema4d_assign_material_async(object_name: str, material_name: str) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("assign_material", {"object": object_name, "material": material_name})


def cinema4d_list_materials() -> Dict:
    """List all materials in the scene."""
    return _run_async(_cinema4d_list_materials_async())


async def _cinema4d_list_materials_async() -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("list_materials", {})


def cinema4d_execute_python(code: str) -> Dict:
    """Execute arbitrary Python code inside Cinema 4D (full C4D Python API access)."""
    return _run_async(_cinema4d_execute_python_async(code))


async def _cinema4d_execute_python_async(code: str) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("execute_python", {"code": code})


def cinema4d_save_scene(path: str) -> Dict:
    """Save the current Cinema 4D project to disk."""
    return _run_async(_cinema4d_save_scene_async(path))


async def _cinema4d_save_scene_async(path: str) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("save_scene", {"path": path})


def cinema4d_load_scene(path: str) -> Dict:
    """Load a .c4d file into the scene."""
    return _run_async(_cinema4d_load_scene_async(path))


async def _cinema4d_load_scene_async(path: str) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("load_scene", {"path": path})


def cinema4d_render(output_path: str = "", frame: int = None, resolution: List[int] = None, renderer: str = "standard") -> Dict:
    """Render the current frame or animation. Renderers: standard, redshift, octane."""
    return _run_async(_cinema4d_render_async(output_path, frame, resolution, renderer))


async def _cinema4d_render_async(output_path: str, frame: int, resolution: List[int], renderer: str) -> Dict:
    client = await _get_c4d_client()
    args = {"renderer": renderer}
    if output_path:
        args["output_path"] = output_path
    if frame is not None:
        args["frame"] = frame
    if resolution:
        args["resolution"] = resolution
    return await client.call_tool("render", args)


def cinema4d_mograph_cloner(object_name: str, mode: str = "grid", count: int = 10, spacing: float = 100.0) -> Dict:
    """Create a MoGraph cloner on an object. Modes: grid, linear, radial, object, honeycomb."""
    return _run_async(_cinema4d_mograph_cloner_async(object_name, mode, count, spacing))


async def _cinema4d_mograph_cloner_async(object_name: str, mode: str, count: int, spacing: float) -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("mograph_cloner", {"object": object_name, "mode": mode, "count": count, "spacing": spacing})


def cinema4d_inspect_redshift_materials() -> Dict:
    """Inspect Redshift materials in the scene (preferred over ad-hoc Python for Redshift)."""
    return _run_async(_cinema4d_inspect_redshift_materials_async())


async def _cinema4d_inspect_redshift_materials_async() -> Dict:
    client = await _get_c4d_client()
    return await client.call_tool("inspect_redshift_materials", {})


def _run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def cinema4d_control(action: str, **kwargs) -> Dict:
    """
    Unified Cinema 4D control entry point.
    
    Actions:
    - ping, get_scene_info, list_objects, get_object_info
    - add_primitive, modify_object, delete_object, group_objects
    - set_keyframe
    - create_material, assign_material, list_materials
    - execute_python
    - save_scene, load_scene
    - render
    - mograph_cloner
    - inspect_redshift_materials
    """
    actions = {
        "ping": cinema4d_ping,
        "get_scene_info": cinema4d_get_scene_info,
        "list_objects": cinema4d_list_objects,
        "get_object_info": lambda: cinema4d_get_object_info(kwargs.get("name", "")),
        "add_primitive": lambda: cinema4d_add_primitive(
            kwargs.get("primitive_type", "cube"),
            kwargs.get("name", ""),
            kwargs.get("position"),
            kwargs.get("rotation"),
            kwargs.get("scale")
        ),
        "modify_object": lambda: cinema4d_modify_object(
            kwargs.get("name", ""),
            kwargs.get("position"),
            kwargs.get("rotation"),
            kwargs.get("scale"),
            kwargs.get("visible")
        ),
        "delete_object": lambda: cinema4d_delete_object(kwargs.get("name", "")),
        "group_objects": lambda: cinema4d_group_objects(kwargs.get("names", []), kwargs.get("group_name", "")),
        "set_keyframe": lambda: cinema4d_set_keyframe(
            kwargs.get("name", ""),
            kwargs.get("property", ""),
            kwargs.get("frame", 0),
            kwargs.get("value")
        ),
        "create_material": lambda: cinema4d_create_material(
            kwargs.get("name", ""),
            kwargs.get("color"),
            kwargs.get("roughness", 0.5),
            kwargs.get("metallic", 0.0),
            kwargs.get("emission")
        ),
        "assign_material": lambda: cinema4d_assign_material(kwargs.get("object_name", ""), kwargs.get("material_name", "")),
        "list_materials": cinema4d_list_materials,
        "execute_python": lambda: cinema4d_execute_python(kwargs.get("code", "")),
        "save_scene": lambda: cinema4d_save_scene(kwargs.get("path", "")),
        "load_scene": lambda: cinema4d_load_scene(kwargs.get("path", "")),
        "render": lambda: cinema4d_render(
            kwargs.get("output_path", ""),
            kwargs.get("frame"),
            kwargs.get("resolution"),
            kwargs.get("renderer", "standard")
        ),
        "mograph_cloner": lambda: cinema4d_mograph_cloner(
            kwargs.get("object_name", ""),
            kwargs.get("mode", "grid"),
            kwargs.get("count", 10),
            kwargs.get("spacing", 100.0)
        ),
        "inspect_redshift_materials": cinema4d_inspect_redshift_materials,
    }

    if action not in actions:
        return {"error": f"Unknown action: {action}. Available: {list(actions.keys())}"}

    try:
        return actions[action]()
    except Exception as e:
        return {"error": f"Cinema 4D control error: {e}"}