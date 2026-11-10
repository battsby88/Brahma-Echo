# MASTER PROMPT: Implement Real Logic for 1,848 Stub Skills in Brahma Echo

## CONTEXT
You are implementing real logic for 1,848 stub skills in the Brahma Echo assistant. The repository is already cloned at `/workspace/app` (or your local path). The skill infrastructure is **already built and working** — you only need to implement the actual logic in each skill's `scripts/run.py`.

## ARCHITECTURE OVERVIEW (TRACE FROM SOURCE)

### Core Pipeline (already built in `/workspace/app`):
```
main.py → BrahmaLive.__init__() 
    → load_skill_tools_at_startup() [core/skill_tool_loader.py]
        → SkillToolLoader.load_all_skill_tools() 
            → reads .claude/skills/{skill}/tools.yaml
            → generates Brahma tool declarations (JSON Schema)
            → registers with TOOL_DECLARATIONS
    → LLM calls tool by name
    → _execute_skill_tool() [main.py:4340]
        → SkillExecutor.execute() [core/skill_executor.py]
            → SandboxExecutor.execute() 
                → subprocess with timeout, resource limits, path validation
                → returns structured JSON
```

### Key Files (DO NOT MODIFY):
- `core/skill_registry.py` — loads 1,855 SKILL.md files
- `core/skill_tool_loader.py` — reads tools.yaml → Brahma tool declarations
- `core/skill_executor.py` — SandboxExecutor with timeout/resource limits/path validation
- `main.py` — BrahmaLive, tool registration, _execute_skill_tool()
- `core/skill_tools.py` — tools.yaml schema definition

## SKILL STRUCTURE (ALREADY GENERATED)

Each skill in `.claude/skills/{skill-name}/` has:
```
skill-name/
├── SKILL.md          # Metadata (name, description, category, version, author)
├── tools.yaml        # Tool declarations (already generated with unique names)
└── scripts/
    └── run.py        # ← YOUR TARGET: Implement real logic here
```

### Example tools.yaml (already generated):
```yaml
skill: aws-cli
version: "1.0"
tools:
  - name: aws-cli_run
    description: "Run AWS CLI operation"
    entrypoint: scripts/run.py
    entrypoint_type: python
    parameters:
      type: object
      properties:
        service:
          type: string
          description: "AWS service (ec2, s3, lambda, etc.)"
        operation:
          type: string
          description: "Operation to perform"
        region:
          type: string
          default: "us-east-1"
    timeout_seconds: 60
    requires_sandbox: true
    returns:
      type: object
      properties:
        success: {type: boolean}
        output: {type: object}
        error: {type: string}
```

### Current Stub run.py (REPLACE THIS):
```python
#!/usr/bin/env python3
"""
aws-cli — Skill runner
"""
import argparse, json, sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--args-file", help="Path to JSON file with arguments")
    args = parser.parse_args()
    if args.args_file:
        with open(args.args_file) as f:
            tool_args = json.load(f)
    else:
        tool_args = {}
    # TODO: Implement aws-cli skill logic here
    result = {
        "success": True,
        "output": {
            "message": "aws-cli skill executed successfully",
            "args_received": tool_args
        }
    }
    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## YOUR TASK

### For each skill in `.claude/skills/` (1,848 skills):
1. **Read** the skill's `SKILL.md` to understand its purpose
2. **Read** the generated `tools.yaml` to see the tool interface
3. **Implement** real logic in `scripts/run.py` replacing the stub
4. **Test** locally: `python scripts/run.py --args-file test_args.json`

## PRIORITY ORDER (HIGH IMPACT FIRST)

### Tier 1: Core Infrastructure (~50 skills)
```
aws-*, gcp-*, azure-*, kubernetes-*, terraform-*, docker-*, 
github-*, gitlab-*, docker-*, kubernetes-*, terraform-*,
postgres-*, mysql-*, redis-*, elasticsearch-*, clickhouse-*, snowflake-*, duckdb-*
```

### Tier 2: AI/ML & Data (~80 skills)
```
langchain-*, langgraph-*, llama-*, huggingface-*, openai-*, anthropic-*,
pytorch-*, tensorflow-*, llamafactory-*, unsloth-*, peft-fine-tuning-*
rag-*, ragas-*, ragflow-*, lightrag-*, llama-index-*, llamaindex-*
```

### Tier 3: 3D/CAD & Creative (~30 skills)
```
blender-*, cinema4d-*, autocad-*, 3dsmax-*, maya-*, houdini-*, zbrush-*
```

### Tier 4: Productivity & Communication (~100 skills)
```
slack-*, discord-*, email-*, notion-*, obsidian-*, linear-*, jira-*, 
notion-*, linear-*, jira-*, github-*, gitlab-*, git-*
```

### Tier 4: Security, Monitoring, Utils (~200 skills)
```
security-*, vault-*, sentry-*, datadog-*, prometheus-*, grafana-*, 
prometheus-*, grafana-*, datadog-*, sentry-*, vault-*, vaultwarden-*
```

### Tier 5: Remaining (~1,500 skills) — Batch process

## IMPLEMENTATION RULES (CRITICAL)

### 1. DO NOT BREAK EXISTING INFRASTRUCTURE
- **Never modify**: `core/skill_*.py`, `main.py`, `dashboard/server.py`, `main.py` tool registration
- **Only touch**: `.claude/skills/{skill}/scripts/run.py`
- **Never change**: `tools.yaml` (already generated with correct schema)

### 2. IMPLEMENTATION PATTERN (FOLLOW EXACTLY)
```python
#!/usr/bin/env python3
"""
{skill-name} — {one-line description}
"""

import argparse
import json
import sys
import subprocess
import os
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--args-file", help="Path to JSON file with arguments")
    args = parser.parse_args()
    
    # Load arguments from file (passed by SkillExecutor)
    if args.args_file:
        with open(args.args_file) as f:
            tool_args = json.load(f)
    else:
        tool_args = {}
    
    # --- YOUR REAL LOGIC HERE ---
    try:
        # Extract parameters
        param1 = tool_args.get("param1", "default")
        param2 = tool_args.get("param2", 10)
        
        # Do real work here (API calls, CLI commands, file ops, etc.)
        result_data = do_real_work(param1, param2)
        
        # SUCCESS: Return structured JSON (last line printed)
        result = {
            "success": True,
            "output": result_data
        }
    except Exception as e:
        # FAILURE: Return error in structured format
        result = {
            "success": False,
            "error": str(e)
        }
    
    # MUST: Print JSON as last line (SkillExecutor parses this)
    print(json.dumps(result))
    return 0 if result["success"] else 1

def do_real_work(param1, param2):
    """Your actual implementation."""
    # Example: subprocess.run, API calls, file operations, etc.
    return {"result": f"Processed {param1} with {param2}"}

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### 3. PARAMETER HANDLING
- **All inputs** come via `--args-file` (JSON file path)
- **Load with**: `json.load(open(args.args_file))`
- **Validate** against tool's JSON Schema (optional but recommended)
- **Return**: Structured JSON via `print(json.dumps(result))`

### 4. SANDBOX CONSTRAINTS (ENFORCED BY EXECUTOR)
| Constraint | Limit |
|------------|-------|
| Timeout | 60s default (configurable in tools.yaml) |
| Memory | 100 MB |
| CPU | 100% of 1 core |
| File access | Only paths in `allowed_paths` (relative to skill dir) |
| Network | Allowed (but respect timeouts) |

### 5. ALLOWED PATHS (from tools.yaml)
```yaml
allowed_paths: ["scripts/", "data/", "output/"]  # Relative to skill directory
```
- Use `Path(__file__).parent.parent / "data" / "file.txt"` for data access
- **Never** access paths outside skill directory

### 5. TESTING LOCALLY
```bash
# Create test args
cat > test_args.json <<'EOF'
{"topic": "AI agents", "tone": "educational", "length_seconds": 60}
EOF

# Run skill directly
cd .claude/skills/yt-script
python scripts/run.py --args-file ../test_args.json

# Expected output (last line only):
# {"success": true, "output": {"script": "...", "word_count": 450, "estimated_duration_seconds": 60}}
```

## SKILL-SPECIFIC GUIDANCE

### AWS Skills (aws-cli, aws-ec2, aws-lambda, etc.)
```python
import boto3
def do_real_work(service, operation, region, **params):
    client = boto3.client(service, region_name=region)
    method = getattr(client, operation)
    return method(**params)
```

### Git/GitHub/GitLab
```python
import subprocess
def do_real_work(operation, repo, **params):
    if operation == "pr":
        # Use gh CLI or GitHub API
        result = subprocess.run(["gh", "pr", "create", ...], capture_output=True, text=True)
        return {"output": result.stdout}
```

### Database (PostgreSQL, MySQL, Redis, etc.)
```python
import psycopg2 / redis / pymongo
def do_real_work(query, database):
    conn = psycopg2.connect(database=database)
    cur = conn.cursor()
    cur.execute(query)
    return {"rows": cur.fetchall()}
```

### Kubernetes/Terraform/Docker
```python
import subprocess
def do_real_work(operation, manifest, dir):
    cmd = ["kubectl", operation, "-f", manifest]  # or terraform, docker
    result = subprocess.run(cmd, cwd=dir, capture_output=True, text=True)
    return {"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode}
```

### AI/ML (OpenAI, Anthropic, Local LLMs)
```python
from openai import OpenAI
def do_real_work(prompt, model, params):
    client = OpenAI()
    response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], **params)
    return {"text": response.choices[0].message.content}
```

### 3D/CAD (Blender, Cinema4D, AutoCAD)
```python
import subprocess
def do_real_work(operation, file, **params):
    # Use MCP servers or direct CLI
    if operation == "render":
        cmd = ["blender", "-b", file, "-o", output, "-f", frame]
        subprocess.run(cmd, check=True)
```

## TESTING CHECKLIST (RUN FOR EACH SKILL)

- [ ] `python scripts/run.py --args-file test_args.json` → returns valid JSON
- [ ] Output has `"success": true/false` and `"output"` or `"error"`
- [ ] Handles missing/invalid args gracefully (returns `success: false, error: "..."`)
- [ ] Respects `allowed_paths` (no absolute paths outside skill dir)
- [ ] Completes within timeout (60s default)
- [ ] No `shell=True` in subprocess calls
- [ ] No `exec()` or `eval()`

## BATCH PROCESSING STRATEGY

### Option A: Manual (High Quality)
```bash
# Process 20-30 skills/day
for skill in .claude/skills/*/; do
    # 1. Read SKILL.md
    # 2. Read tools.yaml
    # 3. Edit scripts/run.py
    # 4. Test with test_args.json
done
```

### Option B: Semi-Automated (Recommended)
```python
# Use this helper to scaffold implementations
# Run once, then manually fill in logic
```

## VERIFICATION (RUN AFTER EACH BATCH)

```bash
# 1. Reload skills in Brahma
python -c "
from core.skill_tool_loader import get_skill_tool_loader
loader = get_skill_tool_loader()
tools = loader.load_all_skill_tools()
print(f'Loaded {len(loader.loaded_tools)} tools')
"

# 2. Run smoke tests
python run_smoke_tests.py

# 3. Test specific skill
cd .claude/skills/yt-script
python scripts/run.py --args-file test_args.json
```

## WHAT NOT TO DO

| ❌ Don't | ✅ Do |
|----------|-------|
| Modify `core/skill_*.py` | Only edit `.claude/skills/*/scripts/run.py` |
| Change `tools.yaml` | Only edit `scripts/run.py` |
| Add `shell=True` | Use `subprocess.run([cmd, args], shell=False)` |
| Use `exec()`/`eval()` | Never |
| Access paths outside skill dir | Use `allowed_paths` only |
| Print debug output | Only final `print(json.dumps(result))` |
| Block >60s | Respect timeout, use async if needed |

## FINAL VERIFICATION

After implementing a batch of skills:
```bash
# 1. All smoke tests pass
python run_smoke_tests.py

# 2. Tool count matches
python -c "from core.skill_tool_loader import get_skill_tool_loader; l=get_skill_tool_loader(); l.load_all_skill_tools(); print(len(l.loaded_tools))"

# 3. Key skills execute
python -c "
import asyncio
from core.skill_executor import execute_skill_tool
from core.skill_registry import get_skill_registry
r=asyncio.run(execute_skill_tool('yt-script','yt-script_run',{'topic':'test'}, get_skill_registry()))
print(r)
"
```

---

## SUMMARY

**You have 1,848 skills to implement.** The infrastructure is complete, tested, and production-ready. Your job is purely **business logic implementation** in `scripts/run.py` for each skill. Follow the pattern exactly, test each one, and work in priority batches. The infrastructure will not break if you follow the rules above.

**Start with Tier 1 (AWS, GCP, K8s, Terraform, Databases, GitHub) — highest impact.**

Good luck. The infrastructure is solid. Now make it useful. 🚀