# SLAIT Backend

This backend executes user-provided x86-64 NASM assembly inside a Docker sandbox, captures program stdout, and captures selected register values at configured source lines.

## Components

- `docker/Dockerfile`
  - Builds the sandbox image (`slait-sandbox:latest`) with NASM, GCC, GDB, Python.
  - Copies runtime scripts to `/app/scripts`.
- `sandbox_scripts/run_pipeline.sh`
  - **In container:** Runs the build + execute + register-capture pipeline.
- `sandbox_scripts/parse_registers_multiline.py`
  - **In container:** Reads `lines.txt`, generates a GDB script, runs GDB in batch mode, writes register dump 
- `run_sandbox_job.py`
  - Host-side runner that creates a container, copies in inputs, runs the pipeline, copies out outputs, and optionally returns parsed JSON.

## End-to-End Flow

1. `run_sandbox_job.py` verifies Docker availability.
2. It creates and starts a container from `slait-sandbox:latest`.
3. It copies host inputs into the container:
   - `/work/program.asm`
   - `/work/lines.txt`
4. It executes:
   - `/app/scripts/run_pipeline.sh /work/program.asm /work/lines.txt`
5. `run_pipeline.sh` performs:
   - Assemble with NASM.
   - Link with GCC.
   - Run binary and capture stdout to `/work/program_output.txt`.
   - Run GDB-based register capture to `/work/register_dump.txt`.
6. `run_sandbox_job.py` copies outputs back to host temp storage, parses register dump, prints text or JSON, then removes the container.

## Inputs

### `program.asm`

- NASM source for x86-64 Linux.
- Example file: `test_run/program.asm`.

### `lines.txt`

- One config per line.
- Format:
  - `line:<N>, <reg1>:<0|1>, <reg2>:<0|1>, ...`
- `line:<N>` is required.
- Any register with flag `1` is captured at that breakpoint.
- Blank lines and `#` comments are ignored.

Example:

```txt
line:9, rax:1, rbx:1, rcx:1
line:10, rax:1, rbx:1, rcx:0
```

## Outputs

Inside the container (under `/work`):

- `program_output.txt`: stdout from the assembled program.
- `register_dump.txt`: raw GDB capture grouped by breakpoint line.

From `run_sandbox_job.py --json`:

- `stdout`: program stdout.
- `breakpoints`: parsed register data per line, including:
  - `hex`
  - `u64`
  - `i64`
  - `bytes_le`
  - `ascii_le`

## Build and Test

Run commands from the repo root (`slait/`).

### 1) Build sandbox image

```bash
docker build -t slait-sandbox:latest -f backend/docker/Dockerfile backend
```

### 2) Test host runner (recommended)

Human-readable output:

```bash
python3 backend/run_sandbox_job.py \
  --asm backend/test_run/program.asm \
  --lines backend/test_run/lines.txt
```

JSON output:

```bash
python3 backend/run_sandbox_job.py \
  --asm backend/test_run/program.asm \
  --lines backend/test_run/lines.txt \
  --json
```

Keep temp output files for debugging:

```bash
python3 backend/run_sandbox_job.py \
  --asm backend/test_run/program.asm \
  --lines backend/test_run/lines.txt \
  --keep-tmp
```

### 3) Test pipeline directly in container

```bash
docker run --rm \
  -v "$(pwd)/backend/test_run:/work" \
  slait-sandbox:latest \
  bash -lc "/app/scripts/run_pipeline.sh /work/program.asm /work/lines.txt"
```

Then inspect generated files on host:

```bash
cat backend/test_run/program_output.txt
cat backend/test_run/register_dump.txt
```

## Troubleshooting

- `Docker does not seem available`
  - Start Docker and verify your user can run `docker version`.
- `ASM file not found` or `lines.txt not found`
  - Verify paths passed to `--asm` and `--lines`.
- Missing `/work/program_output.txt` or `/work/register_dump.txt`
  - The pipeline failed before output generation; inspect logs from `run_sandbox_job.py` output.
- GDB capture is empty
  - Check that `line:<N>` values in `lines.txt` correspond to debuggable lines in your assembly source.
