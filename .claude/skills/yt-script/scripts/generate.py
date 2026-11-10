#!/usr/bin/env python3
"""
YT Script Generator — Generate YouTube scripts from topics
"""

import argparse
import json
import sys
import os


def generate_script(topic: str, tone: str, length_seconds: int, format_type: str) -> dict:
    """Generate a YouTube script based on parameters."""
    
    # Word count estimation (130 words per minute)
    words_per_minute = 130
    target_words = int((length_seconds / 60) * words_per_minute)
    
    # Tone-specific openings
    openings = {
        "educational": f"Today we're diving deep into {topic}. By the end of this video, you'll understand exactly how it works.",
        "entertainment": f"Wait until you see what I discovered about {topic}! This is going to blow your mind.",
        "viral": f"STOP scrolling! You NEED to know about {topic} right now. Here's why everyone's talking about it.",
        "documentary": f"The story of {topic} begins in an unexpected place. What follows will change how you see everything."
    }
    
    # Tone-specific structures
    structures = {
        "educational": [
            "Hook & Promise",
            "Prerequisites/Background",
            "Core Concept 1",
            "Core Concept 2", 
            "Core Concept 3",
            "Real-world Example",
            "Common Mistakes",
            "Summary & Next Steps"
        ],
        "entertainment": [
            "Hook & Tease",
            "The Setup",
            "The Journey",
            "The Reveal",
            "Reaction/Analysis",
            "Bonus/Behind the Scenes",
            "Call to Action"
        ],
        "viral": [
            "Hook (0-3s)",
            "Problem/Agitation",
            "Solution Reveal",
            "Proof/Demo",
            "Why This Matters",
            "Share/CTA"
        ],
        "documentary": [
            "Prologue",
            "Act 1: Origins",
            "Act 2: Conflict",
            "Act 3: Resolution",
            "Epilogue",
            "Reflection"
        ]
    }
    
    opening = openings.get(tone, openings["educational"])
    structure = structures.get(tone, structures["educational"])
    
    # Generate script content
    script_parts = [opening, ""]
    
    words_per_section = target_words // len(structure)
    
    for i, section in enumerate(structure):
        script_parts.append(f"## {section}")
        script_parts.append(f"[Content for {section} - approximately {words_per_section} words]")
        script_parts.append("")
    
    script_parts.append("Thanks for watching! Don't forget to like, subscribe, and hit that notification bell.")
    
    script_text = "\n".join(script_parts)
    actual_word_count = len(script_text.split())
    
    return {
        "script": script_text,
        "word_count": actual_word_count,
        "estimated_duration_seconds": int((actual_word_count / words_per_minute) * 60)
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--args-file", help="Path to JSON file with arguments")
    args = parser.parse_args()
    
    if args.args_file:
        with open(args.args_file) as f:
            tool_args = json.load(f)
    else:
        tool_args = {}
    
    topic = tool_args.get("topic", "")
    tone = tool_args.get("tone", "educational")
    length_seconds = tool_args.get("length_seconds", 300)
    format_type = tool_args.get("format", "script")
    
    if not topic:
        print(json.dumps({"success": False, "error": "topic is required"}))
        return 1
    
    try:
        result = generate_script(topic, tone, length_seconds, format_type)
        output = {"success": True, "output": result}
        print(json.dumps(output))
        return 0
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())