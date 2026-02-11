#!/usr/bin/env bash
set -euo pipefail

ASM_PATH="${1:-}"
LINES_PATH="${2:-}"

if [[ -z "${ASM_PATH}" || -z "${LINES_PATH}" ]]; then
  echo "Usage: run_pipeline.sh <asm_file> <lines.txt>"
  exit 2
fi
if [[ ! -f "${ASM_PATH}" ]]; then
  echo "ERROR: ASM file not found: ${ASM_PATH}"
  exit 3
fi
if [[ ! -f "${LINES_PATH}" ]]; then
  echo "ERROR: lines.txt not found: ${LINES_PATH}"
  exit 4
fi

# Outputs MUST land in the mounted run directory (/work)
OUT_DIR="/work"
PROG_OUT="${OUT_DIR}/program_output.txt"
REG_OUT="${OUT_DIR}/register_dump.txt"

# Internal build workspace inside container (prevents host permission issues)
RUN_ID="$(date +%s%N)"
TMP_DIR="/tmp/slait_build_${RUN_ID}"
mkdir -p "${TMP_DIR}"

OBJ_PATH="${TMP_DIR}/program.o"
BIN_PATH="${TMP_DIR}/program"

PARSE_SCRIPT="/app/scripts/parse_registers_multiline.py"

echo "[SLAIT] Inputs:  ASM=${ASM_PATH}  LINES=${LINES_PATH}"
echo "[SLAIT] Build:   ${TMP_DIR}"
echo "[SLAIT] Outputs: ${PROG_OUT}, ${REG_OUT}"

# Clean old outputs in /work (safe if rerun on same folder)
rm -f "${PROG_OUT}" "${REG_OUT}" 2>/dev/null || true

echo "[1/4] Assembling ..."
nasm -f elf64 -g -F stabs "${ASM_PATH}" -o "${OBJ_PATH}"

echo "[2/4] Linking ..."
gcc -no-pie -nostartfiles -g "${OBJ_PATH}" -o "${BIN_PATH}"

echo "[3/4] Running binary and capturing stdout ..."
"${BIN_PATH}" | tee "${PROG_OUT}" >/dev/null

echo "[4/4] Capturing registers via GDB ..."
pushd "${TMP_DIR}" >/dev/null
python3 "${PARSE_SCRIPT}" "${BIN_PATH}" "${LINES_PATH}" "${REG_OUT}"
popd >/dev/null

echo "[SLAIT] Done."
