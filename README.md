# SLAIT – Secure Language Assembly Inspector Tool

SLAIT is a web-based platform for safely running and inspecting **NASM x86 assembly** programs in a sandboxed environment.  
It allows students and instructors to:

- Paste or upload assembly code
- Define *inspection points* at specific lines
- Capture CPU register and flag states using `gdb`
- View results in a clear, timeline/table-style UI

This repository contains the **full project codebase** (frontend, backend, and sandbox).  
Project documentation and the public-facing website are hosted separately:

- 📄 Docs & milestone artifacts: https://github.com/MBratchr/assembly.github.io  
- 🌐 Project website: https://mbratchr.github.io/assembly.github.io/

---

## 🧩 High-Level Architecture

SLAIT follows a simple client–server + sandbox architecture:

- **Frontend (Angular)**  
  - In-browser code editor for NASM x86
  - UI for creating inspection points (line number + registers/flags)
  - Results view (table/timeline of snapshots)
  - Error display panel for compile/runtime issues

- **Backend API**  
  - Accepts code + inspection definitions from the frontend
  - Orchestrates compilation and execution inside a Docker container
  - Calls `gdb` to capture register/flag states at each inspection point
  - Returns structured results and error messages

- **Sandbox / Execution Environment (Docker)**  
  - Container image with NASM, `gdb`, and required tooling
  - Runs untrusted user code in an isolated environment
  - Enforces timeouts and resource limits to prevent abuse



## 👥 Authors

**Maria Linkins-Nielsen**  
Backend Developer – NASM execution pipeline, Docker sandbox, gdb integration, API design  
GitHub: https://github.com/ginganinja04

**Michael Bratcher**  
Frontend Developer – Angular UI, code editor, inspection interface, results visualization  
GitHub: https://github.com/MBratchr

**Faculty Advisor**  
Dr. Marius Silaghi – Florida Institute of Technology



