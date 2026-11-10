"""
Skill Tools Specification — Standard interface for executable skills
Version: 1.0
"""

TOOLS_YAML_SCHEMA = {
    "type": "object",
    "properties": {
        "skill": {
            "type": "string",
            "description": "Skill name (must match skill directory name)"
        },
        "version": {
            "type": "string",
            "default": "1.0"
        },
        "tools": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "description", "entrypoint"],
                "properties": {
                    "name": {
                        "type": "string",
                        "pattern": "^[a-z][a-z0-9_]*$",
                        "description": "Tool name (snake_case, unique across all skills)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description for LLM"
                    },
                    "entrypoint": {
                        "type": "string",
                        "description": "Relative path to executable (script or module)"
                    },
                    "entrypoint_type": {
                        "type": "string",
                        "enum": ["python", "python_module", "node", "shell", "binary"],
                        "default": "python",
                        "description": "How to execute the entrypoint"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "JSON Schema for tool parameters",
                        "type": "object",
                        "additionalProperties": True
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "default": 60,
                        "minimum": 1,
                        "maximum": 300,
                        "description": "Maximum execution time"
                    },
                    "requires_sandbox": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to run in sandboxed environment"
                    },
                    "allowed_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "Paths the tool is allowed to access (relative to skill dir)"
                    },
                    "env_vars": {
                        "type": "object",
                        "description": "Environment variables to set",
                        "additionalProperties": {"type": "string"}
                    },
                    "returns": {
                        "type": "object",
                        "description": "Expected return value schema"
                    },
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "args": {"type": "object"},
                                "expected": {"type": "object"}
                            }
                        }
                    }
                }
            }
        }
    },
    "required": ["skill", "tools"]
}

# Example tools.yaml for a skill:
EXAMPLE_TOOLS_YAML = """
skill: yt-script
version: "1.0"
tools:
  - name: yt_script_generate
    description: "Generate a YouTube script from a topic with specified tone and length"
    entrypoint: scripts/generate.py
    entrypoint_type: python
    parameters:
      type: object
      properties:
        topic:
          type: string
          description: "The video topic"
        tone:
          type: string
          enum: [educational, entertainment, viral, documentary]
          default: educational
        length_seconds:
          type: integer
          minimum: 30
          maximum: 1800
          default: 300
        format:
          type: string
          enum: [script, outline, bullet_points]
          default: script
    timeout_seconds: 120
    requires_sandbox: true
    allowed_paths: ["scripts/", "templates/"]
    returns:
      type: object
      properties:
        script:
          type: string
        word_count:
          type: integer
        estimated_duration_seconds:
          type: integer
    examples:
      - args:
          topic: "How AI agents work"
          tone: "educational"
          length_seconds: 300
        expected:
          script: "Today we'll explore how AI agents work..."
          word_count: 450
          estimated_duration_seconds: 300
"""

# Entrypoint type handlers
ENTRYPOINT_HANDLERS = {
    "python": "execute_python_script",
    "python_module": "execute_python_module",
    "node": "execute_node_script",
    "shell": "execute_shell_script",
    "binary": "execute_binary"
}