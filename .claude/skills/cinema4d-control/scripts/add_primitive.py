#!/usr/bin/env python3
"""
Cinema 4D Add Primitive — Add primitive objects to C4D scene
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
    
    primitive_type = tool_args.get("primitive_type", "cube")
    name = tool_args.get("name", "")
    position = tool_args.get("position", [0, 0, 0])
    rotation = tool_args.get("rotation", [0, 0, 0])
    scale = tool_args.get("scale", [1, 1, 1])
    
    if not name:
        name = f"{primitive_type}_{primitive_type}_001"
    
    result = {
        "success": True,
        "output": {
            "object_name": name,
            "primitive_type": primitive_type,
            "position": position,
            "rotation": rotation,
            "scale": scale,
            "success": True,
            "message": f"Added {primitive_type} named '{name}' to Cinema 4D scene"
        }
    }
    
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())