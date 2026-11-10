"""
Sandboxed Skill Executor — Safe execution of skill tools
"""

import asyncio
import json
import os
import subprocess
import tempfile
import shlex
import sys
import signal
import resource
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ExecutionResult:
    def __init__(self, success: bool, output: Any = None, error: str = None, 
                 stdout: str = "", stderr: str = "", duration_ms: int = 0):
        self.success = success
        self.output = output
        self.error = error
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms
        }


class SandboxExecutor:
    """Sandboxed executor for skill tools with resource limits."""
    
    def __init__(self, skill_dir: Path, tool_config: Dict[str, Any]):
        self.skill_dir = skill_dir.resolve()
        self.tool_config = tool_config
        self.timeout = tool_config.get("timeout_seconds", 60)
        self.requires_sandbox = tool_config.get("requires_sandbox", True)
        self.allowed_paths = tool_config.get("allowed_paths", [])
        self.env_vars = tool_config.get("env_vars", {})
        self.entrypoint_type = tool_config.get("entrypoint_type", "python")
        self.entrypoint = tool_config.get("entrypoint")
    
    def _validate_path(self, path: Path) -> bool:
        """Check if path is within allowed boundaries."""
        try:
            path = path.resolve()
            # Must be within skill directory
            if not path.is_relative_to(self.skill_dir):
                return False
            # If allowed_paths specified, must be within one of them
            if self.allowed_paths:
                allowed = False
                for allowed_path in self.allowed_paths:
                    allowed_dir = (self.skill_dir / allowed_path).resolve()
                    if path.is_relative_to(allowed_dir):
                        allowed = True
                        break
                if not allowed:
                    return False
            return True
        except Exception:
            return False
    
    def _prepare_env(self) -> Dict[str, str]:
        """Prepare environment variables."""
        env = os.environ.copy()
        env.update(self.env_vars)
        # Add skill directory to Python path
        env["PYTHONPATH"] = f"{self.skill_dir}:{env.get('PYTHONPATH', '')}"
        env["SKILL_DIR"] = str(self.skill_dir)
        return env
    
    def _set_resource_limits(self):
        """Set resource limits for the subprocess."""
        try:
            # Limit CPU time (seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout))
            # Limit memory (100MB)
            resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
            # Limit file size (10MB)
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
            # Limit number of processes
            resource.setrlimit(resource.RLIMIT_NPROC, (50, 50))
        except Exception:
            pass  # Limits not supported on all platforms
    
    async def execute(self, args: Dict[str, Any]) -> ExecutionResult:
        """Execute the skill tool with given arguments."""
        start_time = time.time()
        
        # Validate entrypoint
        if not self.entrypoint:
            return ExecutionResult(False, error="No entrypoint configured")
        
        entrypoint_path = (self.skill_dir / self.entrypoint).resolve()
        if not self._validate_path(entrypoint_path):
            return ExecutionResult(False, error=f"Entrypoint outside allowed paths: {self.entrypoint}")
        
        if not entrypoint_path.exists():
            return ExecutionResult(False, error=f"Entrypoint not found: {self.entrypoint}")
        
        # Prepare execution based on type
        try:
            if self.entrypoint_type == "python":
                return await self._execute_python(entrypoint_path, args)
            elif self.entrypoint_type == "python_module":
                return await self._execute_python_module(args)
            elif self.entrypoint_type == "node":
                return await self._execute_node(entrypoint_path, args)
            elif self.entrypoint_type == "shell":
                return await self._execute_shell(entrypoint_path, args)
            elif self.entrypoint_type == "binary":
                return await self._execute_binary(entrypoint_path, args)
            else:
                return ExecutionResult(False, error=f"Unknown entrypoint type: {self.entrypoint_type}")
        except asyncio.TimeoutError:
            return ExecutionResult(False, error=f"Execution timed out after {self.timeout}s", duration_ms=int((time.time() - start_time) * 1000))
        except Exception as e:
            return ExecutionResult(False, error=f"Execution failed: {str(e)}", duration_ms=int((time.time() - start_time) * 1000))
    
    async def _execute_python(self, script_path: Path, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a Python script with arguments passed via stdin/stdout."""
        # Write args to temp file for script to read
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(args, f)
            args_file = f.name
        
        start_time = time.time()
        
        try:
            # Prepare command
            cmd = [sys.executable, str(script_path), "--args-file", args_file]
            
            # Execute with timeout
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.skill_dir),
                env=self._prepare_env(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._set_resource_limits if self.requires_sandbox else None
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Try to parse JSON output from stdout
            output = None
            if proc.returncode == 0:
                try:
                    # Look for JSON in stdout (last line that's valid JSON)
                    for line in reversed(stdout.decode().strip().split('\n')):
                        try:
                            output = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    pass
            
            return ExecutionResult(
                success=proc.returncode == 0,
                output=output,
                error=stderr.decode() if proc.returncode != 0 else None,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                duration_ms=duration_ms
            )
        finally:
            # Cleanup temp file
            try:
                os.unlink(args_file)
            except Exception:
                pass
    
    async def _execute_python_module(self, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a Python module (e.g., -m skill.module)."""
        # For modules, we pass args via environment or stdin
        import base64
        args_b64 = base64.b64encode(json.dumps(args).encode()).decode()
        
        cmd = [sys.executable, "-m", self.entrypoint]
        env = self._prepare_env()
        env["TOOL_ARGS_B64"] = args_b64
        
        start_time = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.skill_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=self._set_resource_limits if self.requires_sandbox else None
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        output = None
        if proc.returncode == 0:
            try:
                for line in reversed(stdout.decode().strip().split('\n')):
                    try:
                        output = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass
        
        return ExecutionResult(
            success=proc.returncode == 0,
            output=output,
            error=stderr.decode() if proc.returncode != 0 else None,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            duration_ms=duration_ms
        )
    
    async def _execute_node(self, script_path: Path, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a Node.js script."""
        # Write args to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(args, f)
            args_file = f.name
        
        try:
            cmd = ["node", str(script_path), "--args-file", args_file]
            
            start_time = time.time()
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.skill_dir),
                env=self._prepare_env(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=self._set_resource_limits if self.requires_sandbox else None
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            output = None
            if proc.returncode == 0:
                try:
                    for line in reversed(stdout.decode().strip().split('\n')):
                        try:
                            output = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    pass
            
            return ExecutionResult(
                success=proc.returncode == 0,
                output=output,
                error=stderr.decode() if proc.returncode != 0 else None,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                duration_ms=duration_ms
            )
        finally:
            try:
                os.unlink(args_file)
            except Exception:
                pass
    
    async def _execute_shell(self, script_path: Path, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a shell script."""
        # Export args as environment variables
        env = self._prepare_env()
        for key, value in args.items():
            env[f"TOOL_ARG_{key.upper()}"] = json.dumps(value) if not isinstance(value, str) else value
        
        start_time = time.time()
        proc = await asyncio.create_subprocess_exec(
            "bash", str(script_path),
            cwd=str(self.skill_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=self._set_resource_limits if self.requires_sandbox else None
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        output = None
        if proc.returncode == 0:
            try:
                for line in reversed(stdout.decode().strip().split('\n')):
                    try:
                        output = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass
        
        return ExecutionResult(
            success=proc.returncode == 0,
            output=output,
            error=stderr.decode() if proc.returncode != 0 else None,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            duration_ms=duration_ms
        )
    
    async def _execute_binary(self, binary_path: Path, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a compiled binary."""
        # Convert args to command line arguments
        cmd_args = []
        for key, value in args.items():
            cmd_args.append(f"--{key}")
            cmd_args.append(json.dumps(value) if not isinstance(value, str) else value)
        
        cmd = [str(binary_path)] + cmd_args
        
        start_time = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.skill_dir),
            env=self._prepare_env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=self._set_resource_limits if self.requires_sandbox else None
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        output = None
        if proc.returncode == 0:
            try:
                for line in reversed(stdout.decode().strip().split('\n')):
                    try:
                        output = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            except Exception:
                pass
        
        return ExecutionResult(
            success=proc.returncode == 0,
            output=output,
            error=stderr.decode() if proc.returncode != 0 else None,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            duration_ms=duration_ms
        )


# Global executor cache
_executor_cache: Dict[str, SandboxExecutor] = {}


def get_executor(skill_dir: Path, tool_config: Dict[str, Any]) -> SandboxExecutor:
    """Get or create executor for a skill tool."""
    cache_key = f"{skill_dir}:{tool_config.get('name', '')}"
    if cache_key not in _executor_cache:
        _executor_cache[cache_key] = SandboxExecutor(skill_dir, tool_config)
    return _executor_cache[cache_key]


async def execute_skill_tool(skill_name: str, tool_name: str, args: Dict[str, Any], 
                              skill_registry) -> Dict[str, Any]:
    """High-level function to execute a skill tool."""
    # Get skill
    skill = skill_registry.get_skill(skill_name)
    if not skill:
        return {"success": False, "error": f"Skill not found: {skill_name}"}
    
    # Find tool config
    tools_yaml_path = Path(skill["directory"]) / "tools.yaml"
    if not tools_yaml_path.exists():
        return {"success": False, "error": f"No tools.yaml in skill: {skill_name}"}
    
    import yaml
    with open(tools_yaml_path) as f:
        tools_spec = yaml.safe_load(f)
    
    tool_config = None
    for tool in tools_spec.get("tools", []):
        if tool["name"] == tool_name:
            tool_config = tool
            break
    
    if not tool_config:
        return {"success": False, "error": f"Tool not found: {tool_name} in skill {skill_name}"}
    
    # Validate args against schema (basic validation)
    # TODO: Add proper JSON Schema validation
    
    # Execute
    executor = get_executor(Path(skill["directory"]), tool_config)
    result = await executor.execute(args)
    
    return result.to_dict()