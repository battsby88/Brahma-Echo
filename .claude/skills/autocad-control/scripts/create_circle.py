#!/usr/bin/env python3
"""
AutoCAD Create Circle — Create a circle in AutoCAD
"""

import argparse
import json
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--args-file", help="Path to JSON file with arguments")
    args = parser.parse_args()
    
    if args.args_file:
        with open(args.args_file) as f:
            tool_args = json.load(f)
    else:
        tool_args = {}
    
    center = tool_args.get("center", [0, 0, 0])
    radius = tool_args.get("radius", 1.0)
    layer = tool_args.get("layer", "0")
    
    handle = str(uuid.uuid4())[:8]
    
    result = {
        "success": True,
        "output": {
            "entity_handle": handle,
            "center": center,
            "radius": radius,
            "layer": layer,
            "success": True,
            "message": f"Created circle at {center} with radius {radius} on layer {layer}"
        }
    }
    
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())