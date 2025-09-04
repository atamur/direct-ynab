## Project Overview

This is a Python project called "direct-ynab" that is designed for YNAB (You Need A Budget) integration. The project uses a custom parser to read YNAB4 budget files and apply deltas.

## Documentation

- **TASKS.md**: Task backlog and implementation progress
- **LIBS.md**: External library analysis and integration details
- **CLAUDE.md**: This file - general project guidance

## Project Setup

To work with this project:
* Activate the virtual environment: `source ~/.virtualenvs/direct-ynab/bin/activate`
* Run tests: `python -m pytest`
 
## Architecture Notes

When code is added, it should follow Python best practices:

- Use virtual environment for dependency isolation
- Create appropriate project structure (src/, tests/, etc.)
- Add requirements.txt or pyproject.toml for dependency management
- Follow PEP 8 style guidelines

## Code Quality Standards

### TDD and Code Cleanliness Policy
When using TDD methodology (tdd-red-green-refactor agent), maintain strict code quality standards:

- **❌ NO TODO Comments**: Never leave TODO comments or placeholder functionality in committed code
- **❌ NO Unimplemented Code Paths**: Remove all unimplemented features, parameters, or methods that aren't fully functional  
- **✅ Clean API Design**: Method signatures should only include parameters that are actually used and supported
- **✅ Documentation Accuracy**: Docstrings must reflect actual functionality, not planned features
- **✅ Test Coverage**: All code paths must be tested and functional

This policy ensures production-ready code that doesn't mislead future developers with promises of unimplemented features.

### Key Learnings from Phase 1 Implementation

**Dynamic Path Discovery Patterns**:
- Never hardcode file paths or directory names in YNAB4 file parsing
- Always read .ydevice files to extract deviceGUID for locating actual data directories
- Use dynamic discovery methods (`_find_data_dir`, `_find_device_dir`) for robust path resolution

**TDD Testing Standards**:
- Comprehensive test coverage should include error cases, edge cases, and end-to-end workflows
- Use real fixture data (not mocked data) for parser validation to catch real-world issues
- Test count: 24 tests for parser + 14 tests for CLI = 38+ tests for core functionality
- Mock only external dependencies (like lock timeouts), not core business logic

**Pydantic Best Practices**:
- Use `ConfigDict(extra='ignore')` instead of deprecated `Config` class
- Apply consistent configuration patterns across all model classes
- Import `ConfigDict` explicitly from pydantic for clarity

### Key Learnings from past runs

**TDD Quality Assurance Process**:
- Always follow TDD implementation with code-quality-reviewer agent review
- Initial TDD implementations often contain over-engineering that needs to be trimmed
- Code review helps ensure adherence to CLAUDE.md standards (no placeholder code, minimal implementation)
- The review-fix cycle is essential for production-ready code

**Complex System Implementation Patterns**:
- Break complex systems (like YNAB4 write operations) into comprehensive test suites first
- Use real-world fixture data to validate implementation correctness
- Implement graceful failure modes for critical systems where corruption is unacceptable
- Start minimal and only implement what tests require - avoid over-engineering

**Code Consolidation and Refactoring Patterns**:
- Centralization efforts (like path discovery) significantly improve maintainability and consistency
- API design consistency across methods creates predictable and cohesive interfaces
- Even small consolidation changes can have large positive impacts on code quality
- Comprehensive integration testing validates not just individual changes but entire architectural improvements
- The TDD → Code Quality Review cycle ensures both functional correctness and adherence to standards

**Test Suite Optimization and Coverage Analysis**:
- Proactive test duplication analysis prevents maintenance bloat and improves test suite efficiency
- Functional tests (parser, writer, integration) often provide better coverage than isolated unit tests
- Test consolidation can reduce suite size significantly (e.g., 15% reduction) while maintaining 100% coverage
- Existing comprehensive test suites may already cover new functionality through different testing approaches
- Regular test suite reviews help identify and eliminate redundant test scenarios

## External Dependencies Integration Checklist

When adding new external libraries, ALWAYS follow this checklist to avoid oversights:

### ✅ Required Steps:
1. **Install the dependency** in the virtual environment
2. **Add to pyproject.toml dependencies** (with proper version constraints or git URLs)
3. **Analyze and document** in LIBS.md (capabilities, limitations, integration strategy)
4. **Update TASKS.md** to reflect completion status and reference documentation
5. **Test the integration** to ensure it works correctly

### ✅ Documentation Standards:
- **LIBS.md**: Must include status, repository, installation method, capabilities, limitations, and integration recommendations
- **TASKS.md**: Must update current status and mark tasks complete with findings summary
- **CLAUDE.md**: Should reference new documentation when it affects project-wide concerns

## Project Structure
```
direct-ynab/
├── src/
│   ├── ynab_io/          # Data Access Layer
│   │   ├── models.py     # Pydantic models for YNAB entities
│   │   ├── parser.py     # Custom YNAB4 file parser
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