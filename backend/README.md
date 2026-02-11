# SLAIT Backend

## Sandbox image
- Docker image contains: NASM, GCC, GDB, Python
- Scripts live in `/app/scripts`

## Pipeline
- `run_pipeline.sh` orchestrates:
  1) assemble
  2) link
  3) run
  4) register tracking via GDB

## Inputs
- `/work/program.asm`
- `/work/lines.txt`

## Outputs (inside container)
- `/work/program_output.txt`
- `/work/register_dump.txt`

