#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
import os 

def parse_config_line(raw: str):
    """
    Input example:
      line:9, rax:1, rbx:0, rcx:1
    Returns:
      (line_number:int, tracked_registers:list[str])
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts or not parts[0].startswith("line:"):
        raise ValueError(f"Bad config line (missing line:...): {raw!r}")

    line_str = parts[0].split(":", 1)[1].strip()
    if not line_str.isdigit():
        raise ValueError(f"Bad line number in: {raw!r}")

    line_no = int(line_str)

    tracked = []
    for item in parts[1:]:
        if ":" not in item:
            continue
        reg, flag = item.split(":", 1)
        reg = reg.strip()
        flag = flag.strip()
        if flag == "1":
            tracked.append(reg)
    return line_no, tracked

def load_lines_config(lines_path: Path):
    configs = []
    for raw in lines_path.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        line_no, tracked = parse_config_line(raw)
        configs.append((line_no, tracked))
    if not configs:
        raise ValueError("lines.txt contained no valid config lines.")
    return configs

def generate_gdb_script(configs, binary_path: str, out_path: str):
    with open("inspect.gdb", "w") as f:
        f.write("set pagination off\n")
        f.write("set confirm off\n")
        f.write(f"set logging file {out_path}\n")
        f.write("set logging overwrite on\n")
        f.write("set logging enabled on\n")
        f.write(f"file {binary_path}\n\n")

        # Create breakpoints first
        for (line_no, _) in configs:
            f.write(f"break {line_no}\n")
        f.write("\n")

        # Attach commands to each breakpoint (1-indexed in creation order)
        for idx, (line_no, tracked_regs) in enumerate(configs, start=1):
            f.write(f"commands {idx}\n")
            f.write(f'  echo \\n=== Breakpoint at line {line_no} ===\\n\n')
            if tracked_regs:
                for reg in tracked_regs:
                    f.write(f'  printf "{reg}: %lx\\n", ${reg}\n')
            else:
                f.write('  echo (No registers selected)\\n\n')
            f.write("  continue\n")
            f.write("end\n\n")

        f.write("run\n")
        f.write("quit\n")

def run_gdb(binary_path: str, out_path: str):
    subprocess.run(["gdb", "-q", "-batch", "-x", "inspect.gdb"], check=False)

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 parse_registers_multiline.py <binary> <lines.txt> <out_path>")
        sys.exit(1)

    binary_path = sys.argv[1]
    lines_path = Path(sys.argv[2])
    out_path = sys.argv[3]

    if os.path.exists(out_path):
        os.remove(out_path)
    if os.path.exists("inspect.gdb"):
        os.remove("inspect.gdb")


    if not lines_path.exists():
        print(f"ERROR: lines file not found: {lines_path}")
        sys.exit(2)

    try:
        configs = load_lines_config(lines_path)
    except Exception as e:
        print(f"ERROR parsing lines file: {e}")
        sys.exit(3)

    generate_gdb_script(configs, binary_path, out_path)
    run_gdb(binary_path, out_path)

if __name__ == "__main__":
    main()
