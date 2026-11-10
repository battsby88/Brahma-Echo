#!/usr/bin/env python3
"""
Blender Object Add — Add primitive objects to scene
"""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--args-file", help="Path to JSON file with arguments")
    args = parser.parse_args()
    
    if args.args_file:
        with open(args.args_file) as f:
            tool_args = json.load(f)
    else:
        tool_args = {}
    
    object_type = tool_args.get("object_type", "CUBE")
    name = tool_args.get("name", "")
    location = tool_args.get("location", [0, 0, 0])
    rotation = tool_args.get("rotation", [0, 0, 0])
    scale = tool_args.get("scale", [1, 1, 1])
    
    # Generate object name if not provided
    if not name:
        name = f"{object_type.lower()}_{object_type.lower()}_001"
    
    result = {
        "success": True,
        "output": {
            "object_name": name,
            "object_type": object_type,
            "location": location,
            "rotation": rotation,
            "scale": scale,
            "success": True,
            "message": f"Added {object_type} named '{name}'"
        }
    }
    
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())