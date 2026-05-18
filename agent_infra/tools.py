### here is where the tools will live...
from pathlib import Path
import subprocess 
import shlex

WORKSPACE_ROOT = Path(__file__).resolve().parent

OVERALL_BANNED_TERMINAL_USES = {
    "rm",
    "rmdir",
    "sudo",
    "su",
    "chmod",
    "chown",
    "curl",
    "wget",
    "ssh",
    "scp",
    "shutdown",
    "reboot",
    "halt",
    "dd",
    "mkfs",
    "diskutil",
    "installer",
    "brew",
    "pip",
    "pip3",
    "npm",
    "npx",
    "yarn",
    "pnpm",
}

BANNED_SHELL_OPERATORS = ()
BANNED_TERMINAL_TOKENS = {"install", "uninstall", "upgrade", "update", "autoremove"}
### do memory later
"""
def write_memory(text):
    path = Path("/Users/eligross/Desktop/local_agent_infra/agent_infra/memory/mem.md")
    with open(path, 'a') as f:
        f.write(text)


def read_memory():
    path = Path("/Users/eligross/Desktop/local_agent_infra/agent_infra/memory/mem.md")
    with open(path) as f:
        ### read the file and return the text 
        return"""

### general terminal use --> lots of ability

def terminal(line, timeout=30):
    try:
        args = shlex.split(line)
    except ValueError as error:
        return {"ok": False, "blocked": True, "error": f"Could not parse command: {error}"}

    if not args:
        return {"ok": False, "blocked": True, "error": "Empty command"}

    for operator in BANNED_SHELL_OPERATORS:
        if operator in line:
            return {"ok": False, "blocked": True, "error": f"Blocked shell operator: {operator}"}

    command = Path(args[0]).name
    tokens = {Path(arg).name.lower() for arg in args}
    if tokens & OVERALL_BANNED_TERMINAL_USES:
        return {"ok": False, "blocked": True, "error": f"Blocked command: {sorted(tokens & OVERALL_BANNED_TERMINAL_USES)[0]}"}
    if tokens & BANNED_TERMINAL_TOKENS:
        return {"ok": False, "blocked": True, "error": f"Blocked install/system token: {sorted(tokens & BANNED_TERMINAL_TOKENS)[0]}"}

    try:
        result = subprocess.run(
            line,
            cwd=WORKSPACE_ROOT,
            shell=True,
            executable="/bin/zsh",
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "blocked": False, "error": f"Command timed out after {timeout}s"}
    except FileNotFoundError:
        return {"ok": False, "blocked": False, "error": f"Command not found: {command}"}

    return {
        "ok": result.returncode == 0,
        "blocked": False,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

"""
### subagent spawning capability --> call itself basically
### this agent also has to have read write power in the memory and is instiated with a goal
def subagent():
    return
"""
