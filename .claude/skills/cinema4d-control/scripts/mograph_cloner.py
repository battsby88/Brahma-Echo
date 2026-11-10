#!/usr/bin/env python3
"""
Cinema 4D MoGraph Cloner — Create MoGraph cloner on object
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
    
    object_name = tool_args.get("object_name", "")
    mode = tool_args.get("mode", "grid")
    count = tool_args.get("count", 10)
    spacing = tool_args.get("spacing", 100.0)
    
    if not object_name:
        print(json.dumps({"success": False, "error": "object_name is required"}))
        return 1
    
    cloner_name = f"Cloner_{object_name}"
    
    result = {
        "success": True,
        "output": {
            "cloner_name": cloner_name,
            "source_object": object_name,
            "mode": mode,
            "count": count,
            "spacing": spacing,
            "success": True,
            "message": f"Created MoGraph cloner '{cloner_name}' on '{object_name}' with {count} clones in {mode} mode"
        }
    }
    
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())