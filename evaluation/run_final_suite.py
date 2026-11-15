"""Run one frozen, isolated suite; stop the current child before exiting.

All stages share a lock and immutable output directory. This prevents abandoned
shell sequences from starting another worker or overwriting an ongoing report.
"""

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src import config
from .run_benchmark import implementation_hash


def run(out_dir: Path, logs_dir: Path, *, check_only=False):
    frozen_path = config.PROJECT_ROOT / "evaluation" / "benchmark" / "frozen_config.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if implementation_hash() != frozen["implementation_sha256"]:
        raise ValueError("Code đã đổi sau khi chốt cấu hình; cần xem lại dev trước khi chạy test")
    lock_path = config.PROJECT_ROOT / ".cache" / "evaluation-suite.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    child = None

    def stop(signum, frame):
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            # Never call wait() inside a signal handler: the interrupted wait
            # may already hold Popen's non-reentrant waitpid lock.
        raise KeyboardInterrupt

    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Đã có một suite đang chạy. Không chạy chồng các phép đo.") from exc
        if check_only:
            print("Frozen code and suite lock OK", flush=True)
            return
        out_dir, logs_dir = out_dir.resolve(), logs_dir.resolve()
        stages = [(split, system) for split in ("dev", "test") for system in ("baseline", "hybrid")]
        if any((out_dir / f"{split}_{system}.json").exists() for split, system in stages):
            raise ValueError("Thư mục đã có báo cáo. Chọn --out-dir và --logs-dir mới để không ghi đè.")
        out_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        started = datetime.now(timezone.utc).isoformat()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        for split, system in stages:
            output = out_dir / f"{split}_{system}.json"
            log_path = logs_dir / f"{split}_{system}.log"
            command = [sys.executable, "-m", "evaluation.run_benchmark", "--split", split,
                       "--system", system, "--answers", "--out", str(output)]
            print(f"START {split}/{system}: {output}", flush=True)
            with log_path.open("w", encoding="utf-8") as log:
                child = subprocess.Popen(command, cwd=config.PROJECT_ROOT, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)
                code = child.wait()
                child = None
            if code:
                raise RuntimeError(f"{split}/{system} lỗi {code}; dừng suite, xem {log_path}")
            result = json.loads(output.read_text(encoding="utf-8"))
            if not result["complete"] or result["implementation_sha256"] != frozen["implementation_sha256"]:
                raise ValueError("Báo cáo chưa đầy đủ hoặc không đúng cấu hình đóng băng")
            print(f"DONE {split}/{system}: {len(result['results'])} questions", flush=True)
        manifest = {"started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
                    "implementation_sha256": frozen["implementation_sha256"], "frozen_config": frozen,
                    "complete": True, "reports": [f"{split}_{system}.json" for split, system in stages]}
        (out_dir / "suite_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=config.PROJECT_ROOT / "evaluation" / "final")
    parser.add_argument("--logs-dir", type=Path, default=config.PROJECT_ROOT / "docs" / "final")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        run(args.out_dir, args.logs_dir, check_only=args.check_only)
    except KeyboardInterrupt:
        parser.exit(130, "Suite đã dừng; không khởi chạy stage tiếp theo.\n")
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Lỗi suite: {exc}\n")


if __name__ == "__main__":
    main()
