#!/usr/bin/env python3
import re
from typing import Dict, List, Any

BP_RE = re.compile(r"^=== Breakpoint at line (\d+) ===$")
REG_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9]{1,4}):\s+([0-9a-fA-F]+)$")

def parse_register_dump(raw: str) -> List[Dict[str, Any]]:
    """
    Parses register_dump.txt into structured breakpoints.
    Expected format:
      === Breakpoint at line 9 ===
      rax: 1
      rbx: 0
    """
    breakpoints: List[Dict[str, Any]] = []
    current = None

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        m = BP_RE.match(line)
        if m:
            # start new breakpoint block
            if current is not None:
                breakpoints.append(current)
            current = {"line": int(m.group(1)), "registers": {}}
            continue

        m = REG_RE.match(line)
        if m and current is not None:
            reg = m.group(1)
            val = m.group(2)
            current["registers"][reg] = val
            continue

        # ignore everything else (gdb noise)

    if current is not None:
        breakpoints.append(current)

    return breakpoints