"""Stopping evaluation must stop its child without waiting on an acquired lock."""

import subprocess
import sys


def test_suite_stop_does_not_deadlock_inside_child_wait(tmp_path):
    script = r'''
import json, os, signal, subprocess, sys, threading
from pathlib import Path
from evaluation import run_final_suite as suite
root = Path(sys.argv[1])
suite.config.PROJECT_ROOT = root
suite.implementation_hash = lambda: "test-hash"
folder = root / "evaluation" / "benchmark"
folder.mkdir(parents=True)
(folder / "frozen_config.json").write_text(json.dumps({"implementation_sha256": "test-hash"}))
real_popen = subprocess.Popen
def child(*args, **kwargs):
    process = real_popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
    (root / "child.pid").write_text(str(process.pid))
    threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
    return process
suite.subprocess.Popen = child
try:
    suite.run(root / "out", root / "logs")
except KeyboardInterrupt:
    print("interrupted without deadlock", flush=True)
'''
    process = subprocess.run([sys.executable, "-c", script, str(tmp_path)],
                             capture_output=True, text=True, timeout=8)
    assert process.returncode == 0, process.stderr
    assert "interrupted without deadlock" in process.stdout
