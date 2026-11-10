"""
Skill Registry for Brahma Echo - Loads and manages agent skills from .claude/skills/
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional


class SkillRegistry:
    """Manages agent skills following the open Agent Skills standard."""
    
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            skills_dir = str(Path(__file__).parent.parent / ".claude" / "skills")
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Dict] = {}
        self.loaded = False
    
    def load_skills(self) -> Dict[str, Dict]:
        """Load all skills from the skills directory."""
        if not self.skills_dir.exists():
            print(f"[SkillRegistry] Skills directory not found: {self.skills_dir}")
            return {}
        
        self.skills = {}
        
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("."):
                continue
            
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            try:
                skill_data = self._parse_skill_md(skill_md, skill_dir)
                if skill_data:
                    self.skills[skill_data["name"]] = skill_data
                    print(f"[SkillRegistry] Loaded skill: {skill_data['name']}")
            except Exception as e:
                print(f"[SkillRegistry] Failed to load {skill_dir.name}: {e}")
        
        self.loaded = True
        print(f"[SkillRegistry] Loaded {len(self.skills)} skills")
        return self.skills
    
    def _parse_skill_md(self, skill_md: Path, skill_dir: Path) -> Optional[Dict]:
        """Parse SKILL.md frontmatter and extract skill metadata."""
        content = skill_md.read_text(encoding="utf-8")
        
        # Extract frontmatter (YAML between ---)
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except Exception:
                    # Fallback: simple key: value parsing
                    for line in parts[1].split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            frontmatter[k.strip()] = v.strip().strip('"')
        
        # Get skill name from frontmatter or directory name
        name = frontmatter.get("name", skill_dir.name)
        description = frontmatter.get("description", "")
        version = frontmatter.get("version", "1.0.0")
        author = frontmatter.get("author", "")
        license_ = frontmatter.get("license", "")
        
        # Check for executable scripts
        scripts = []
        for ext in [".py", ".js", ".sh", ".ts"]:
            scripts.extend(skill_dir.rglob(f"*{ext}"))
        
        # Check for references directory
        references = {}
        refs_dir = skill_dir / "references"
        if refs_dir.exists():
            for ref_file in refs_dir.iterdir():
                if ref_file.is_file():
                    references[ref_file.stem] = str(ref_file)
        
        return {
            "name": name,
            "description": description,
            "version": version,
            "author": author,
            "license": license_,
            "directory": str(skill_dir),
            "skill_md": str(skill_md),
            "scripts": [str(s) for s in scripts],
            "references": references,
            "frontmatter": frontmatter,
        }
    
    def get_skill(self, name: str) -> Optional[Dict]:
        """Get a skill by name."""
        if not self.loaded:
            self.load_skills()
        return self.skills.get(name)
    
    def list_skills(self) -> List[Dict]:
        """List all loaded skills."""
        if not self.loaded:
            self.load_skills()
        return list(self.skills.values())
    
    def get_skills_by_category(self, category: str) -> List[Dict]:
        """Filter skills by category (from frontmatter)."""
        if not self.loaded:
            self.load_skills()
        return [s for s in self.skills.values() if s["frontmatter"].get("category") == category]
    
    def invoke_skill_script(self, skill_name: str, script_name: str, args: List[str]) -> Dict:
        """Invoke a skill's executable script."""
        skill = self.get_skill(skill_name)
        if not skill:
            return {"error": f"Skill not found: {skill_name}"}
        
        # Find the script
        script_path = None
        for s in skill["scripts"]:
            if Path(s).name == script_name or Path(s).stem == script_name:
                script_path = s
                break
        
        if not script_path:
            return {"error": f"Script not found: {script_name} in skill {skill_name}"}
        
        try:
            import subprocess
            cmd = ["python", script_path] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=skill["directory"])
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Script execution timeout"}
        except Exception as e:
            return {"error": f"Script execution failed: {e}"}


# Global instance
_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get the global skill registry instance."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry


def load_skills_at_startup() -> Dict[str, Dict]:
    """Load all skills at application startup."""
    registry = get_skill_registry()
    return registry.load_skills()


if __name__ == "__main__":
    # Test
    registry = SkillRegistry()
    skills = registry.load_skills()
    for name, skill in skills.items():
        print(f"\n{name}:")
        print(f"  Description: {skill['description'][:80]}...")
        print(f"  Scripts: {len(skill['scripts'])}")
        print(f"  References: {list(skill['references'].keys())}")