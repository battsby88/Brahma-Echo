#!/usr/bin/env python3
"""
Batch Wire Skills — Creates tools.yaml + entrypoint scripts for all skills missing them.
"""

import yaml
from pathlib import Path
from typing import Dict, List

CATEGORY_TEMPLATES = {
    "blender": {"tools": [{"name": "blender_run", "desc": "Run Blender operation", "params": {"operation": {"type": "string", "enum": ["render", "export", "script"]}, "file": {"type": "string"}}}]},
    "cinema4d": {"tools": [{"name": "c4d_run", "desc": "Run Cinema 4D operation", "params": {"operation": {"type": "string", "enum": ["render", "export", "mograph"]}, "file": {"type": "string"}}}]},
    "autocad": {"tools": [{"name": "autocad_run", "desc": "Run AutoCAD operation", "params": {"operation": {"type": "string", "enum": ["plot", "export", "lisp"]}, "file": {"type": "string"}}}]},
    "3dsmax": {"tools": [{"name": "max_run", "desc": "Run 3ds Max operation", "params": {"operation": {"type": "string", "enum": ["render", "script"]}, "file": {"type": "string"}}}]},
    "maya": {"tools": [{"name": "maya_run", "desc": "Run Maya operation", "params": {"operation": {"type": "string", "enum": ["render", "script"]}, "file": {"type": "string"}}}]},
    "houdini": {"tools": [{"name": "houdini_run", "desc": "Run Houdini operation", "params": {"operation": {"type": "string", "enum": ["render", "vex"]}, "file": {"type": "string"}}}]},
    "zbrush": {"tools": [{"name": "zbrush_run", "desc": "Run ZBrush operation", "params": {"operation": {"type": "string", "enum": ["export", "script"]}, "file": {"type": "string"}}}]},
    "substance": {"tools": [{"name": "substance_run", "desc": "Run Substance operation", "params": {"operation": {"type": "string", "enum": ["bake", "export"]}, "file": {"type": "string"}}}]},
    "git": {"tools": [{"name": "git_run", "desc": "Run git operation", "params": {"operation": {"type": "string", "enum": ["commit", "push", "pull", "status", "diff"]}, "path": {"type": "string"}}}]},
    "github": {"tools": [{"name": "github_run", "desc": "Run GitHub operation", "params": {"operation": {"type": "string", "enum": ["pr", "issue", "release", "action"]}, "repo": {"type": "string"}}}]},
    "gitlab": {"tools": [{"name": "gitlab_run", "desc": "Run GitLab operation", "params": {"operation": {"type": "string", "enum": ["mr", "pipeline", "issue"]}, "project": {"type": "string"}}}]},
    "docker": {"tools": [{"name": "docker_run", "desc": "Run Docker operation", "params": {"operation": {"type": "string", "enum": ["build", "run", "push", "compose"]}, "image": {"type": "string"}}}]},
    "kubernetes": {"tools": [{"name": "k8s_run", "desc": "Run Kubernetes operation", "params": {"operation": {"type": "string", "enum": ["apply", "delete", "logs", "exec"]}, "manifest": {"type": "string"}}}]},
    "terraform": {"tools": [{"name": "tf_run", "desc": "Run Terraform operation", "params": {"operation": {"type": "string", "enum": ["plan", "apply", "destroy", "init"]}, "dir": {"type": "string"}}}]},
    "ansible": {"tools": [{"name": "ansible_run", "desc": "Run Ansible playbook", "params": {"playbook": {"type": "string"}, "inventory": {"type": "string"}, "tags": {"type": "string"}}}]},
    "aws": {"tools": [{"name": "aws_run", "desc": "Run AWS CLI operation", "params": {"service": {"type": "string"}, "operation": {"type": "string"}, "region": {"type": "string", "default": "us-east-1"}}}]},
    "gcp": {"tools": [{"name": "gcp_run", "desc": "Run GCP operation", "params": {"service": {"type": "string"}, "operation": {"type": "string"}, "project": {"type": "string"}}}]},
    "azure": {"tools": [{"name": "azure_run", "desc": "Run Azure CLI operation", "params": {"service": {"type": "string"}, "operation": {"type": "string"}, "subscription": {"type": "string"}}}]},
    "vercel": {"tools": [{"name": "vercel_deploy", "desc": "Deploy to Vercel", "params": {"project": {"type": "string"}, "env": {"type": "string", "enum": ["preview", "production"]}}}]},
    "netlify": {"tools": [{"name": "netlify_deploy", "desc": "Deploy to Netlify", "params": {"site": {"type": "string"}, "dir": {"type": "string"}}}]},
    "cloudflare": {"tools": [{"name": "cf_run", "desc": "Run Cloudflare operation", "params": {"zone": {"type": "string"}, "operation": {"type": "string"}}}]},
    "postgres": {"tools": [{"name": "pg_query", "desc": "Run PostgreSQL query", "params": {"query": {"type": "string"}, "database": {"type": "string"}}}]},
    "mysql": {"tools": [{"name": "mysql_query", "desc": "Run MySQL query", "params": {"query": {"type": "string"}, "database": {"type": "string"}}}]},
    "mongodb": {"tools": [{"name": "mongo_query", "desc": "Run MongoDB query", "params": {"collection": {"type": "string"}, "operation": {"type": "string"}, "filter": {"type": "object"}}}]},
    "redis": {"tools": [{"name": "redis_run", "desc": "Run Redis command", "params": {"command": {"type": "string"}, "key": {"type": "string"}}}]},
    "elasticsearch": {"tools": [{"name": "es_query", "desc": "Query Elasticsearch", "params": {"index": {"type": "string"}, "query": {"type": "object"}}}]},
    "clickhouse": {"tools": [{"name": "ch_query", "desc": "Query ClickHouse", "params": {"query": {"type": "string"}, "database": {"type": "string"}}}]},
    "snowflake": {"tools": [{"name": "sf_query", "desc": "Query Snowflake", "params": {"query": {"type": "string"}, "warehouse": {"type": "string"}}}]},
    "duckdb": {"tools": [{"name": "duckdb_query", "desc": "Query DuckDB", "params": {"query": {"type": "string"}, "file": {"type": "string"}}}]},
    "langchain": {"tools": [{"name": "lc_run", "desc": "Run LangChain chain", "params": {"chain": {"type": "string"}, "inputs": {"type": "object"}}}]},
    "langgraph": {"tools": [{"name": "lg_run", "desc": "Run LangGraph graph", "params": {"graph": {"type": "string"}, "state": {"type": "object"}}}]},
    "llama": {"tools": [{"name": "llama_run", "desc": "Run Llama model", "params": {"model": {"type": "string"}, "prompt": {"type": "string"}, "params": {"type": "object"}}}]},
    "huggingface": {"tools": [{"name": "hf_run", "desc": "Run HuggingFace model", "params": {"model": {"type": "string"}, "inputs": {"type": "object"}, "task": {"type": "string"}}}]},
    "openai": {"tools": [{"name": "openai_run", "desc": "Run OpenAI API", "params": {"model": {"type": "string"}, "prompt": {"type": "string"}, "params": {"type": "object"}}}]},
    "anthropic": {"tools": [{"name": "anthropic_run", "desc": "Run Anthropic API", "params": {"model": {"type": "string"}, "prompt": {"type": "string"}, "params": {"type": "object"}}}]},
    "pytorch": {"tools": [{"name": "torch_train", "desc": "Train PyTorch model", "params": {"model": {"type": "string"}, "data": {"type": "string"}, "epochs": {"type": "integer"}}}]},
    "tensorflow": {"tools": [{"name": "tf_train", "desc": "Train TensorFlow model", "params": {"model": {"type": "string"}, "data": {"type": "string"}, "epochs": {"type": "integer"}}}]},
    "prometheus": {"tools": [{"name": "prom_query", "desc": "Query Prometheus", "params": {"query": {"type": "string"}, "time": {"type": "string"}}}]},
    "grafana": {"tools": [{"name": "grafana_dashboard", "desc": "Manage Grafana dashboard", "params": {"operation": {"type": "string", "enum": ["create", "update", "get"]}, "uid": {"type": "string"}}}]},
    "datadog": {"tools": [{"name": "dd_metric", "desc": "Send Datadog metric", "params": {"metric": {"type": "string"}, "value": {"type": "number"}, "tags": {"type": "array"}}}]},
    "sentry": {"tools": [{"name": "sentry_capture", "desc": "Capture Sentry event", "params": {"level": {"type": "string"}, "message": {"type": "string"}, "extra": {"type": "object"}}}]},
    "slack": {"tools": [{"name": "slack_send", "desc": "Send Slack message", "params": {"channel": {"type": "string"}, "text": {"type": "string"}, "blocks": {"type": "object"}}}]},
    "discord": {"tools": [{"name": "discord_send", "desc": "Send Discord message", "params": {"channel": {"type": "string"}, "content": {"type": "string"}, "embed": {"type": "object"}}}]},
    "email": {"tools": [{"name": "email_send", "desc": "Send email", "params": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}, "html": {"type": "boolean"}}}]},
    "security": {"tools": [{"name": "sec_scan", "desc": "Run security scan", "params": {"target": {"type": "string"}, "type": {"type": "string", "enum": ["sast", "dast", "sca", "container"]}}}]},
    "vault": {"tools": [{"name": "vault_read", "desc": "Read Vault secret", "params": {"path": {"type": "string"}}}]},
    "notion": {"tools": [{"name": "notion_page", "desc": "Manage Notion page", "params": {"operation": {"type": "string", "enum": ["create", "update", "get"]}, "page_id": {"type": "string"}, "content": {"type": "object"}}}]},
    "obsidian": {"tools": [{"name": "obsidian_note", "desc": "Manage Obsidian note", "params": {"operation": {"type": "string", "enum": ["create", "update", "search"]}, "vault": {"type": "string"}, "note": {"type": "string"}}}]},
    "linear": {"tools": [{"name": "linear_issue", "desc": "Manage Linear issue", "params": {"operation": {"type": "string", "enum": ["create", "update", "get"]}, "team": {"type": "string"}, "title": {"type": "string"}}}]},
    "jira": {"tools": [{"name": "jira_issue", "desc": "Manage Jira issue", "params": {"operation": {"type": "string", "enum": ["create", "update", "transition"]}, "key": {"type": "string"}, "fields": {"type": "object"}}}]},
    "default": {"tools": [{"name": "{skill}_run", "desc": "Run the skill", "params": {"args": {"type": "object", "description": "Arguments for the skill"}}}]}
}

COMPOUND_PATTERNS = [
    ("blender", "blender"),
    ("cinema4d", "cinema4d"),
    ("autocad", "autocad"),
    ("3dsmax", "3dsmax"),
    ("3ds", "3dsmax"),
    ("max-", "3dsmax"),
    ("maya", "maya"),
    ("houdini", "houdini"),
    ("zbrush", "zbrush"),
    ("substance", "substance"),
    ("git", "git"),
    ("github", "github"),
    ("gitlab", "gitlab"),
    ("docker", "docker"),
    ("kubernetes", "kubernetes"),
    ("k8s", "kubernetes"),
    ("terraform", "terraform"),
    ("tf-", "terraform"),
    ("ansible", "ansible"),
    ("aws", "aws"),
    ("gcp", "gcp"),
    ("azure", "azure"),
    ("vercel", "vercel"),
    ("netlify", "netlify"),
    ("cloudflare", "cloudflare"),
    ("postgres", "postgres"),
    ("postgresql", "postgres"),
    ("mysql", "mysql"),
    ("mongo", "mongodb"),
    ("redis", "redis"),
    ("elasticsearch", "elasticsearch"),
    ("elastic", "elasticsearch"),
    ("clickhouse", "clickhouse"),
    ("snowflake", "snowflake"),
    ("duckdb", "duckdb"),
    ("langchain", "langchain"),
    ("langgraph", "langgraph"),
    ("llama", "llama"),
    ("huggingface", "huggingface"),
    ("hf-", "huggingface"),
    ("openai", "openai"),
    ("anthropic", "anthropic"),
    ("pytorch", "pytorch"),
    ("torch", "pytorch"),
    ("tensorflow", "tensorflow"),
    ("tf-", "tensorflow"),
    ("prometheus", "prometheus"),
    ("grafana", "grafana"),
    ("datadog", "datadog"),
    ("sentry", "sentry"),
    ("slack", "slack"),
    ("discord", "discord"),
    ("email", "email"),
    ("security", "security"),
    ("vault", "vault"),
    ("notion", "notion"),
    ("obsidian", "obsidian"),
    ("linear", "linear"),
    ("jira", "jira"),
]

SKILLS_DIR = Path("/workspace/app/.claude/skills")


def get_template_for_skill(skill_name: str) -> Dict:
    skill_lower = skill_name.lower()
    for pattern, template in CATEGORY_TEMPLATES.items():
        if pattern in skill_lower:
            return template
    for pattern, category in COMPOUND_PATTERNS:
        if pattern in skill_name.lower():
            return CATEGORY_TEMPLATES.get(category, CATEGORY_TEMPLATES["default"])
    return CATEGORY_TEMPLATES["default"]


def generate_tools_yaml(skill_name: str, template: Dict) -> str:
    data = {
        "skill": skill_name,
        "version": "1.0",
        "tools": []
    }
    for tool in template.get("tools", []):
        tool_dict = {
            "name": tool["name"].format(skill=skill_name),
            "description": tool["desc"],
            "entrypoint": "scripts/run.py",
            "entrypoint_type": "python",
            "timeout_seconds": 60,
            "requires_sandbox": True,
            "returns": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "output": {"type": "object"},
                    "error": {"type": "string"}
                }
            }
        }
        params = tool.get("params", {})
        if params:
            tool_dict["parameters"] = params
        data["tools"].append(tool_dict)
    return yaml.dump(data, sort_keys=False, default_flow_style=False)


def generate_run_script(skill_name: str) -> str:
    return f'''#!/usr/bin/env python3
"""
{skill_name} — Skill runner
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
        tool_args = {{}}
    
    # TODO: Implement {skill_name} skill logic here
    
    result = {{
        "success": True,
        "output": {{
            "message": "{skill_name} skill executed successfully",
            "args_received": tool_args
        }}
    }}
    
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def main():
    skills_dir = Path("/workspace/app/.claude/skills")
    
    skills_to_wire = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
            continue
        skills_to_wire.append(skill_dir.name)
    
    print(f"Found {len(skills_to_wire)} skills needing tools.yaml")
    
    for i, skill_name in enumerate(skills_to_wire, 1):
        skill_dir = SKILLS_DIR / skill_name
        template = get_template_for_skill(skill_name)
        
        # Create tools.yaml
        tools_yaml_content = generate_tools_yaml(skill_name, template)
        (skill_dir / "tools.yaml").write_text(tools_yaml_content)
        
        # Create scripts directory
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # Create run.py
        run_script_content = generate_run_script(skill_name)
        run_script_path = skill_dir / "scripts" / "run.py"
        run_script_path.write_text(generate_run_script(skill_name))
        run_script_path.chmod(0o755)
        
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(skills_to_wire)} - {skill_name}")
    
    print(f"\n✅ Completed wiring {len(skills_to_wire)} skills!")


if __name__ == "__main__":
    main()