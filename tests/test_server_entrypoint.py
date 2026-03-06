import os
import subprocess
import time
from pathlib import Path


def test_module_entrypoint_starts_without_runpy_warning():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    process = subprocess.Popen(
        [str(repo_root / ".venv" / "bin" / "python"), "-m", "klayout_mcp.server"],
        cwd=repo_root,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(1.0)
        process.terminate()
        _, stderr = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert "RuntimeWarning" not in stderr
