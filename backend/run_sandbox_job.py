#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import json
import re
from typing import Any, Dict, List
## from parse_register_dump import parse_register_dump

_BP_RE = re.compile(r"^=== Breakpoint at line (\d+) ===$")
# Accept: rax: 0x1  OR  rax: 1  (handles both until you standardize)
_REG_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9]{1,4}):\s+(0x[0-9a-fA-F]+|[0-9a-fA-F]+)$")

def parse_register_dump(raw: str) -> List[Dict[str, Any]]:
    """
    Parse register_dump.txt content into structured breakpoints.

    Expected blocks:
      === Breakpoint at line 9 ===
      rax: 0x1
      rbx: 0x0

    Ignores all other GDB noise.
    Returns:
      [
        {"line": 9, "registers": {"rax": "0x1", "rbx": "0x0"}},
        ...
      ]
    """
    breakpoints: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None

    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = _BP_RE.match(line)
        if m:
            if current is not None:
                breakpoints.append(current)
            current = {"line": int(m.group(1)), "registers": {}}
            continue

        m = _REG_RE.match(line)
        if m and current is not None:
            reg = m.group(1)
            val = m.group(2)
            # Normalize values: ensure 0x prefix for hex-looking values if missing
            if not val.startswith("0x"):
                # if it contains any a-f chars, treat as hex
                if any(c in "abcdefABCDEF" for c in val):
                    val = "0x" + val.lower()
                else:
                    # treat as decimal -> keep as-is or convert; keeping as-is is fine for now
                    pass
            current["registers"][reg] = val
            continue

        # Ignore everything else (Breakpoint X at..., warnings, inferior exit, etc.)

    if current is not None:
        breakpoints.append(current)

    return breakpoints

def sh(cmd: list[str], *, check: bool = True, capture: bool = False, text: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command safely (no shell=True)."""
    if capture:
        return subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text)
    return subprocess.run(cmd, check=check)


def ensure_docker_available() -> None:
    try:
        sh(["docker", "version"], check=True, capture=True)
    except Exception as e:
        raise RuntimeError("Docker does not seem available. Is Docker running and are you in the docker group?") from e


def run_job(
    image: str,
    asm_path: Path,
    lines_path: Path,
    pipeline_cmd: list[str],
    keep_tmp: bool = False,
) -> tuple[str, str, str]:
    """
    Returns (stdout_text, register_dump_text, docker_logs_text).
    """
    if not asm_path.exists():
        raise FileNotFoundError(f"ASM file not found: {asm_path}")
    if not lines_path.exists():
        raise FileNotFoundError(f"lines.txt file not found: {lines_path}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="slait_job_"))
    out_dir = tmp_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    cid = None
    logs = ""

    try:
        # Create container (not started yet). Use a long sleep so we can docker exec.
        create = sh(
            ["docker", "create", image, "bash", "-lc", "sleep infinity"],
            capture=True,
            check=True,
        )
        cid = create.stdout.strip()
        if not cid:
            raise RuntimeError("Failed to create container (no container id returned).")

        # Start it
        sh(["docker", "start", cid], check=True)

        # Copy inputs into container
        sh(["docker", "cp", str(asm_path), f"{cid}:/work/program.asm"], check=True)
        sh(["docker", "cp", str(lines_path), f"{cid}:/work/lines.txt"], check=True)

        # Run pipeline inside container (capture logs)
        exec_res = sh(["docker", "exec", cid, *pipeline_cmd], check=False, capture=True)
        logs = (exec_res.stdout or "") + ("\n" if exec_res.stdout else "") + (exec_res.stderr or "")

        if exec_res.returncode != 0:
            # Try to fetch any partial outputs anyway for debugging
            # (docker cp will fail if file doesn't exist)
            pass

        # Copy outputs out (expected locations inside container)
        # These match your pipeline: /work/program_output.txt and /work/register_dump.txt
        # If either is missing, we'll raise with a helpful message.
        prog_out_host = out_dir / "program_output.txt"
        reg_out_host = out_dir / "register_dump.txt"

        try:
            sh(["docker", "cp", f"{cid}:/work/program_output.txt", str(prog_out_host)], check=True)
        except Exception:
            raise RuntimeError(
                "Pipeline did not produce /work/program_output.txt inside the container.\n"
                "Check docker logs below.\n"
                f"--- Docker logs ---\n{logs}"
            )

        try:
            sh(["docker", "cp", f"{cid}:/work/register_dump.txt", str(reg_out_host)], check=True)
        except Exception:
            raise RuntimeError(
                "Pipeline did not produce /work/register_dump.txt inside the container.\n"
                "Check docker logs below.\n"
                f"--- Docker logs ---\n{logs}"
            )

        stdout_text = prog_out_host.read_text(errors="replace")
        reg_text = reg_out_host.read_text(errors="replace")

        breakpoints = parse_register_dump(reg_text)

        bps = parse_register_dump(reg_text)
        payload = {
            "ok": True,
            "stdout": stdout_text,
            "breakpoints": breakpoints,
            "raw_register_dump": reg_text,  # keep for debugging; can remove later
            "metadata": {
                "image": args.image,
            },
        }       

        print(json.dumps(payload, indent=2))

        if exec_res.returncode != 0:
            raise RuntimeError(
                f"Pipeline returned non-zero exit code: {exec_res.returncode}\n"
                f"--- Docker logs ---\n{logs}\n"
                f"--- program_output.txt ---\n{stdout_text}\n"
                f"--- register_dump.txt ---\n{reg_text}\n"
            )

        return stdout_text, reg_text, logs

    finally:
        # Always cleanup container
        if cid:
            try:
                sh(["docker", "rm", "-f", cid], check=False, capture=True)
            except Exception:
                pass

        # Cleanup temp outputs unless you want to keep them
        if not keep_tmp:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            print(f"[SLAIT] Kept temp dir: {tmp_dir}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SLAIT sandbox job (copy-in, exec, copy-out).")
    parser.add_argument("--image", default="slait-sandbox:latest", help="Docker image tag (default: slait-sandbox:latest)")
    parser.add_argument("--asm", required=True, help="Path to program.asm on host")
    parser.add_argument("--lines", required=True, help="Path to lines.txt on host")
    parser.add_argument("--keep-tmp", action="store_true", help="Keep temp output directory for debugging")
    args = parser.parse_args()

    ensure_docker_available()

    asm_path = Path(args.asm).resolve()
    lines_path = Path(args.lines).resolve()

    # Pipeline command inside container (no shell). Adjust here if your path changes.
    pipeline_cmd = ["bash", "-lc", "/app/scripts/run_pipeline.sh /work/program.asm /work/lines.txt"]

    try:
        stdout_text, reg_text, logs = run_job(
            image=args.image,
            asm_path=asm_path,
            lines_path=lines_path,
            pipeline_cmd=pipeline_cmd,
            keep_tmp=args.keep_tmp,
        )
    except Exception as e:
        print(f"[SLAIT] ERROR: {e}", file=sys.stderr)
        return 1

    print("===== program_output.txt =====")
    print(stdout_text.rstrip("\n"))
    print("\n===== register_dump.txt =====")
    print(reg_text.rstrip("\n"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
