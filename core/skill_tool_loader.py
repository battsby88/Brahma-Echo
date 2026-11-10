"""
Skill Tool Loader — Auto-generates tool declarations from skills
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from core.skill_registry import get_skill_registry


class SkillToolLoader:
    """Loads tools.yaml from skills and generates tool declarations."""
    
    def __init__(self):
        self.loaded_tools: Dict[str, Dict] = {}  # tool_name -> tool_spec
        self.tool_to_skill: Dict[str, str] = {}  # tool_name -> skill_name
    
    def load_all_skill_tools(self) -> Dict[str, Dict]:
        """Load tools.yaml from all skills and return tool declarations."""
        registry = get_skill_registry()
        skills = registry.list_skills()
        
        self.loaded_tools = {}
        self.tool_to_skill = {}
        
        for skill in skills:
            skill_dir = Path(skill["directory"])
            tools_yaml_path = skill_dir / "tools.yaml"
            
            if not tools_yaml_path.exists():
                continue
            
            try:
                with open(tools_yaml_path) as f:
                    tools_spec = yaml.safe_load(f)
                
                if not tools_spec or "tools" not in tools_spec:
                    continue
                
                skill_name = tools_spec.get("skill", skill["name"])
                
                for tool in tools_spec["tools"]:
                    tool_name = tool["name"]
                    
                    # Check for duplicates
                    if tool_name in self.loaded_tools:
                        print(f"[SkillToolLoader] Duplicate tool name: {tool_name} (in {skill_name}, already in {self.tool_to_skill[tool_name]})")
                        continue
                    
                    # Build full tool declaration
                    tool_decl = self._build_tool_declaration(skill_name, tool)
                    self.loaded_tools[tool_name] = tool_decl
                    self.tool_to_skill[tool_name] = skill_name
                    
            except Exception as e:
                print(f"[SkillToolLoader] Failed to load tools from {skill['name']}: {e}")
        
        return self.loaded_tools
    
    def _build_tool_declaration(self, skill_name: str, tool: Dict) -> Dict:
        """Convert skill tool spec to Brahma tool declaration."""
        # Build parameters schema
        params_schema = tool.get("parameters", {"type": "object", "properties": {}})
        
        # Ensure it has proper structure
        if "type" not in params_schema:
            params_schema = {"type": "object", "properties": params_schema}
        
        return {
            "name": tool["name"],
            "description": f"[{skill_name}] {tool['description']}",
            "parameters": {
                "type": "OBJECT",
                "properties": params_schema.get("properties", {}),
                "required": params_schema.get("required", [])
            },
            "skill_metadata": {
                "skill_name": skill_name,
                "entrypoint": tool["entrypoint"],
                "entrypoint_type": tool.get("entrypoint_type", "python"),
                "timeout_seconds": tool.get("timeout_seconds", 60),
                "requires_sandbox": tool.get("requires_sandbox", True),
                "allowed_paths": tool.get("allowed_paths", []),
                "env_vars": tool.get("env_vars", {}),
                "returns": tool.get("returns", {})
            }
        }
    
    def get_tool_declaration(self, tool_name: str) -> Optional[Dict]:
        """Get a specific tool declaration."""
        return self.loaded_tools.get(tool_name)
    
    def get_skill_for_tool(self, tool_name: str) -> Optional[str]:
        """Get the skill name for a tool."""
        return self.tool_to_skill.get(tool_name)
    
    def list_tools(self) -> List[Dict]:
        """List all loaded tools."""
        return list(self.loaded_tools.values())
    
    def get_tools_by_skill(self, skill_name: str) -> List[Dict]:
        """Get all tools for a specific skill."""
        return [
            tool for tool in self.loaded_tools.values() 
            if tool.get("skill_metadata", {}).get("skill_name") == skill_name
        ]


# Global loader instance
_tool_loader: Optional[SkillToolLoader] = None


def get_skill_tool_loader() -> SkillToolLoader:
    global _tool_loader
    if _tool_loader is None:
        _tool_loader = SkillToolLoader()
    return _tool_loader


def load_skill_tools_at_startup() -> Dict[str, Dict]:
    """Load all skill tools at application startup."""
    loader = get_skill_tool_loader()
    return loader.load_all_skill_tools()


def get_skill_tool_declarations() -> List[Dict]:
    """Get all tool declarations for Brahma's tool system."""
    loader = get_skill_tool_loader()
    return loader.list_tools()


# Integration with Brahma's main.py
def register_skill_tools_with_brahma() -> int:
    """Register all skill tools with Brahma's tool system.
    
    Returns number of tools registered.
    """
    from main import TOOL_DECLARATIONS
    
    loader = get_skill_tool_loader()
    tools = loader.load_all_skill_tools()
    
    count = 0
    for tool in loader.list_tools():
        # Check if already registered (by name)
        if not any(t["name"] == tool["name"] for t in TOOL_DECLARATIONS):
            TOOL_DECLARATIONS.append(tool)
            count += 1
    
    print(f"[SkillToolLoader] Registered {count} new skill tools")
    return count