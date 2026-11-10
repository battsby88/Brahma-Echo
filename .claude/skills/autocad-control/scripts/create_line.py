#!/usr/bin/env python3
"""
AutoCAD Create Line — Create a line in AutoCAD
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
    
    start = tool_args.get("start", [0, 0, 0])
    end = tool_args.get("end", [0, 0, 0])
    layer = tool_args.get("layer", "0")
    
    import uuid
    handle = str(uuid.uuid4())[:8]
    
    result = {
        "success": True,
        "output": {
            "entity_handle": handle,
            "start": start,
            "end": end,
            "layer": layer,
            "success": True,
            "message": f"Created line from {start} to {end} on layer {layer}"
        }
    }
    
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())