"""Execute candidate Python only inside an unprivileged Linux namespace sandbox."""

import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / ".tmp"


def execute(workspace: Path, code: str, payload=None, timeout: float = 6) -> dict:
    """Run a bounded child with no host home, network, secrets, or writable mounts.

    Only /usr and the explicitly supplied candidate workspace are mounted read-only.
    stdout/stderr are capped by a hard file-size resource limit. The caller owns
    parsing and checking; candidate code never runs in the scorer process.
    """
    TMP.mkdir(exist_ok=True)
    command = [
        "/usr/bin/bwrap",
        "--unshare-user",
        "--unshare-all",
        "--disable-userns",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "ALL",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        str(workspace.resolve()),
        "/workspace",
        "--chdir",
        "/workspace",
        "--clearenv",
        "--setenv",
        "PATH",
        "/usr/bin",
        "--setenv",
        "PYTHONDONTWRITEBYTECODE",
        "1",
        "--",
        "/usr/bin/prlimit",
        "--as=268435456:268435456",
        "--cpu=3:3",
        "--fsize=65536:65536",
        "--nofile=64:64",
        "--nproc=0:0",
        "--core=0:0",
        "/usr/bin/python3",
        "-I",
        "-c",
        code,
    ]
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(dir=TMP, prefix="sandbox-output-") as capture:
        out, err = Path(capture) / "stdout", Path(capture) / "stderr"
        with out.open("wb") as stdout, err.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                env={"PATH": "/usr/bin"},
                start_new_session=True,
            )
            timed_out = False
            try:
                process.communicate(json.dumps(payload).encode(), timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)
        return {
            "returncode": process.returncode,
            "timed_out": timed_out,
            "stdout": out.read_text(errors="replace")[:16000],
            "stderr": err.read_text(errors="replace")[:4000],
            "seconds": time.perf_counter() - started,
        }


APP_RUNNER = """import json, sys
sys.path.insert(0, '/workspace')
from app import handle
print(json.dumps(handle(json.load(sys.stdin)), sort_keys=True))
"""


def invoke(workspace: Path, request: dict) -> dict:
    result = execute(workspace, APP_RUNNER, request)
    try:
        result["response"] = json.loads(result["stdout"]) if result["returncode"] == 0 else None
    except (ValueError, TypeError):
        result["response"] = None
    return result


def visible_checks(workspace: Path) -> dict:
    return execute(
        workspace,
        "import sys, runpy; sys.path.insert(0, '/workspace'); runpy.run_path('/workspace/test_visible.py', run_name='__main__')",
    )
