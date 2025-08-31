# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a fresh Python project called "direct-ynab" that appears to be designed for YNAB (You Need A Budget) integration. The project is currently in its initial state with only development environment setup completed.

## Documentation

- **TASKS.md**: Task backlog and implementation progress
- **LIBS.md**: External library analysis and integration details
- **CLAUDE.md**: This file - general project guidance

## Development Environment

- **Language**: Python 3.12.3
- **Virtual Environment**: Located at `~/.virtualenvs/direct-ynab/`
- **IDE**: PyCharm/IntelliJ IDEA configuration present

## Project Setup

To work with this project:

1. Activate the virtual environment:
   ```bash
   source ~/.virtualenvs/direct-ynab/bin/activate
   ```

2. Install dependencies (once requirements.txt or pyproject.toml is created):
   ```bash
   pip install -r requirements.txt
   # or
   pip install -e .
   ```

## Architecture Notes

This project is in its initial state. When code is added, it should follow Python best practices:

- Use virtual environment for dependency isolation
- Create appropriate project structure (src/, tests/, etc.)
- Add requirements.txt or pyproject.toml for dependency management
- Follow PEP 8 style guidelines

## Common Development Commands

Since this is a fresh project, standard Python development commands will apply once the codebase is established:

- **Run tests**: `python -m pytest` (once pytest is configured)
- **Lint code**: `python -m flake8` or `python -m pylint` (once linting tools are added)
- **Format code**: `python -m black .` (once black is configured)

## External Dependencies Integration Checklist

When adding new external libraries, ALWAYS follow this checklist to avoid oversights:

### ✅ Required Steps:
1. **Install the dependency** in the virtual environment
2. **Add to pyproject.toml dependencies** (with proper version constraints or git URLs)
3. **Analyze and document** in LIBS.md (capabilities, limitations, integration strategy)
4. **Update TASKS.md** to reflect completion status and reference documentation
5. **Test the integration** to ensure it works correctly

### ✅ Common Oversights to Avoid:
- ❌ Installing but not adding to pyproject.toml (dependencies won't be tracked)
- ❌ Adding to pyproject.toml but not documenting in LIBS.md (future developers lack context)
- ❌ Completing analysis but not updating task status in TASKS.md
- ❌ Not testing import/basic functionality after installation
- ❌ Not documenting critical limitations or workarounds needed

### ✅ Documentation Standards:
- **LIBS.md**: Must include status, repository, installation method, capabilities, limitations, and integration recommendations
- **TASKS.md**: Must update current status and mark tasks complete with findings summary
- **CLAUDE.md**: Should reference new documentation when it affects project-wide concerns

## Project Structure
```
direct-ynab/
├── src/
│   ├── ynab_io/          # Data Access Layer (Integration of pynab/php-ynab4)
│   │   ├── models.py     # Pydantic models or extensions/wrappers for pynab models
│   │   ├── reader.py     # State reconstruction (Snapshot + Diffs)
│   │   ├── writer.py     # Delta generation (.ydiff)
│   │   ├── device_manager.py # Device registration and Knowledge tracking
│   │   └── safety.py     # Backup and Locking
│   ├── categorization/   # AI Logic Layer
│   │   ├── engine.py     # Hybrid strategy (L1/L2)
│   │   ├── llm_client.py
│   │   └── transformer.py # Data prep (Object to DataFrame)
│   ├── simulation/       # Business Logic Layer (Risk Mitigation)
│   │   └── simulator.py
│   ├── orchestration/    # Workflow and CLI
│   │   ├── cli.py
│   │   └── workflow.py
├── tests/
│   ├── fixtures/         # Mock YNAB4 budget files (Provided by User)
│   └── ...
├── CLAUDE.md             # Claude AI Agent general instructions (To be updated as needed)
├── TASKS.md              # Backlog of tasks for AI agent (split into IN PROGRESS and DONE sections)
└── pyproject.toml
```