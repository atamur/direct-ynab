### YNAB4 AI Automation

### AI Agent Instructions

**TASK IMPLEMENTATION LOOP:**
Read CLAUDE.md and afterward - these instructions carefully and follow them step by step.

Use TodoWrite tool to write down all the 6 steps below before you start.

0. **Review code structure and details** - Use CLAUDE.md and LIBS.md for reference
1. **Pick next task sequentially** - Pick with the next available task from Phase 0, 1, 2, 3, 4, or 5
2. **Follow TDD methodology** - Use tdd-red-green-refactor agent to implement the task. Each task has GOAL/APPROACH/TEST_CASES structure
3. **Review the code diff** - Use code-quality-reviewer agent. Review the changes made to the code and make sure they are correct, if any feedback send it back to step (3). 
4. **Mark task complete** - MOVE COMPLETED TASK TO "TASKS DONE" SECTION (cut from IN PROGRESS and paste into TASKS DONE with completion details)
5. **Append learnings to the task** - Update the task you just moved with learnings that could be useful in the future
6. **Append global learnings to CLAUDE.md, TASKS.md, and LIBS.md** - Think "how could i have achieved the goal faster?" If anything comes up add that to the relevant documents.

**⚠️ CRITICAL: Task Completion Standards**
Before marking any task as complete, ALWAYS verify these items:
- ✅ **Dependencies added to pyproject.toml** (if any new libraries were used)
- ✅ **Documentation updated** (LIBS.md for external libraries, relevant sections for code changes)
- ✅ **Task status updated** (mark as completed with summary in TASKS.md)
- ✅ **Tests passing** (run full test suite to ensure no regressions)
- ✅ **Integration verified** (test that new functionality actually works end-to-end)

### AI Agent Task Backlog : IN PROGRESS

**CURRENT STATUS:** Phase 1 completed with comprehensive TDD implementation. Phase 2 Tasks 2.1-2.2 completed with comprehensive write logic analysis and device management. All tests passing (76/76). Next task: 2.3 (Port Knowledge Management)

#### Code Review Suggestions

  * **TASK 2.3: Refactor `YnabParser` for Robust Path Discovery**
      * **GOAL:** Improve the parser's robustness by reading all `.ydevice` files to dynamically and accurately identify the active device and its data directory.
      * **APPROACH:** Refactor `_find_device_dir` to read all `.ydevice` files and use the information within them to correctly identify the active device and its corresponding data directory.
      * **TEST_CASES:** The parser correctly identifies the active device in a multi-device setup. The parser correctly falls back to a default device if no active device can be determined.
  * **TASK 2.4: Consolidate Path Discovery Logic**
      * **GOAL:** Centralize all budget-related path discovery into a single `PathManager` class or within the `DeviceManager`.
      * **APPROACH:** Create a centralized `PathManager` or add methods to an existing class (like `DeviceManager`) to handle all budget-related path discovery. This would include finding the `data1~*` directory, the `devices` directory, and the specific device's data directory. All other classes would then use this single source of truth for path information.
      * **TEST_CASES:** The `PathManager` correctly finds all required paths. Other classes correctly use the `PathManager` to get path information.
  * **TASK 2.5: Enhance CLI Error Handling and User Feedback**
      * **GOAL:** Implement more specific error handling in `ynab_io/orchestration/cli.py` to provide users with more precise and actionable feedback.
      * **APPROACH:** Enhance the error handling in the CLI to provide more specific and actionable error messages to the user. For instance, catch more specific exceptions and provide tailored messages. Additionally, the `locked_budget_operation` context manager could be improved to provide more granular error messages about why a lock could not be acquired.
      * **TEST_CASES:** The CLI provides specific error messages for different error conditions. The `locked_budget_operation` context manager provides specific error messages for lock acquisition failures.

#### Phase 2: The Write Layer - Porting `php-ynab4`

**Reference:** Analyze `php-ynab4` source code.

  * **TASK 2.3: (TDD) Port Knowledge Management (src/ynab_io/device_manager.py)**
      * **GOAL:** Correctly track and increment the budget version.
      * **APPROACH:** Port the logic for calculating current global knowledge (by reading all `.ydevice` files) and generating the next sequential version stamp.
      * **TEST_CASES:** Correctly identifies the latest version across multiple mock devices. Generates the correct next version string.
  * **TASK 2.4: (TDD) Port `.ydiff` Generation and Writing (src/ynab_io/writer.py)**
      * **GOAL:** Generate a valid `.ydiff` file containing the changes.
      * **APPROACH:** Implement `DeltaWriter`. Collect "dirty" entities. Serialize them into the exact JSON format (ensure camelCase serialization). Update the `entityVersion` of the modified entities during serialization. Determine the correct filename and write it to the tool's device directory.
      * **TEST_CASES:** Generates a valid JSON structure matching YNAB4 specs. Uses the correct filename. Writes the file to the correct location. Updates the `.ydevice` file after writing.
  * **TASK 2.5: (TDD) Integration Test: Read-Modify-Write Cycle**
      * **GOAL:** Verify the end-to-end data integrity.
      * **APPROACH:** Load budget -> Modify a transaction in memory -> Write the `.ydiff` -> Read the budget again -> Verify the change is present and the structure is valid.

#### Phase 3: Data Transformation and AI Preparation

  * **TASK 3.1: (TDD) Transform to Tabular Format (src/categorization/transformer.py)**
      * **GOAL:** Prepare data for AI analysis (Pandas DataFrame).
      * **APPROACH:** Convert the in-memory object model (Budget State) into a DataFrame. Denormalize the data (join transactions with accounts, payees, and categories to include names, not just IDs).
      * **TEST_CASES:** Correct mapping of fields. Handling of split transactions. Correct handling of dates and milliunits.
  * **TASK 3.2: (TDD) Feature Engineering (src/categorization/transformer.py)**
      * **GOAL:** Clean data for better AI performance.
      * **APPROACH:** Implement text cleaning for raw payee names and memos (e.g., removing store numbers, normalizing whitespace, standardizing case).
      * **TEST_CASES:** "STARBUCKS #1234" becomes "starbucks".

#### Phase 4: AI/LLM Integration - Hybrid Strategy

**Dependencies:** `openai` or `anthropic` (depending on LLM choice).

  * **TASK 4.1: (TDD) L1 - Deterministic Categorization (src/categorization/engine.py)**
      * **GOAL:** Apply high-confidence historical matching before using LLMs.
      * **APPROACH:** Analyze the historical DataFrame. Implement logic to find the most frequent category for a given payee if the consistency is high (e.g., >95%).
      * **TEST_CASES:** Correctly identifies high-confidence matches. Ignores low-confidence matches.
  * **TASK 4.2: (TDD) L2 - LLM Client and Prompt Engineering (src/categorization/llm_client.py)**
      * **GOAL:** Use LLMs to categorize ambiguous or new transactions.
      * **APPROACH:** Implement `LLMClient`. Design precise prompts including: Transaction details, the user's full category hierarchy, and *few-shot examples* dynamically selected from the user's history. Instruct the LLM to return structured JSON (`NormalizedPayeeName`, `PredictedCategoryName`).
      * **TEST_CASES:** Prompt generation is correct. Mock LLM API calls. Response parsing and validation handle structured JSON and potential LLM errors.
  * **TASK 4.3: (TDD) Payee Standardization and Rule Creation (src/categorization/engine.py)**
      * **GOAL:** Clean up payee names and create YNAB rules for future imports.
      * **APPROACH:** Process the `NormalizedPayeeName`. Find the existing Payee entity or create a new one. **Crucially**, create a new `PayeeRenamingRule` entity (using the model from Task 1.4) mapping the raw input payee to the standardized payee.
      * **TEST_CASES:** Correctly creates/finds standardized Payee. Generates a valid `PayeeRenamingRule` object.
  * **TASK 4.4: (TDD) Categorization Pipeline (src/categorization/engine.py)**
      * **GOAL:** Combine L1 and L2 logic and apply changes to the in-memory state.
      * **APPROACH:** Implement the workflow (L1 -> L2). Update the `Transaction`, `Payee`, and `PayeeRenamingRule` objects in memory. Ensure these objects are marked as "dirty" (Task 1.4).
      * **TEST_CASES:** End-to-end categorization test on a list of uncategorized transactions.

#### Phase 5: Workflow Orchestration and Safety Simulation

  * **TASK 5.1: (TDD) Implement Budget Simulator (src/simulation/simulator.py)**
      * **GOAL:** Mitigate the "Temporal Ripple Effect" (Section VI of analysis).
      * **APPROACH:** Implement `ChangeSimulator`. Apply proposed changes in a sandboxed memory state. Implement basic YNAB logic (category rollover, "To Be Budgeted" calculation) to recalculate the state for the affected month and *all subsequent months* to detect downstream impacts.
      * **TEST_CASES:** Detects if a change causes a negative "To Be Budgeted" or uncovered overspending in the current or future months.
  * **TASK 5.2: (TDD) Full Workflow Orchestration (src/orchestration/workflow.py)**
      * **GOAL:** Combine all phases into a safe, sequential workflow.
      * **APPROACH:** Implement the master workflow: Lock -> Backup -> Load -> Analyze/Predict -> Simulate -> Review (CLI output) -> Save (if confirmed) -> Unlock.
  * **TASK 5.3: (TDD) CLI and Dry Run (src/orchestration/cli.py)**
      * **GOAL:** Provide a user interface and safety check.
      * **APPROACH:** Implement CLI (e.g., using `Typer` or `argparse`). Command: `ynab-ai categorize --budget-path <path> [--dry-run]`. Implement interactive confirmation showing proposed changes AND simulation results.
      * **TEST_CASES:** Dry run executes the full pipeline but does not write files. Confirmation prompt correctly gates the write operation.
  * **TASK 5.4: Logging and Error Handling**
      * **GOAL:** Ensure robustness and traceability.
      * **APPROACH:** Implement comprehensive logging throughout the application. Ensure robust error handling that guarantees the lock is always released, even if the process fails.

### AI Agent Task Backlog : TASKS DONE

#### Phase 0: Project Setup and Safety Protocols

  * **TASK 0.1: Environment Initialization** ✅ **COMPLETED**
      * **GOAL:** Set up the project structure and testing framework.
      * **APPROACH:** Initialize the directory structure as defined above, configure `pyproject.toml`, and set up `pytest`.
      * **COMPLETED:** 2025-08-31 - Project structure created, pyproject.toml configured with all dependencies, pytest framework installed and verified with passing tests.
  * **TASK 0.2: (TDD) Backup Utility (src/ynab_io/safety.py)** ✅ **COMPLETED**
      * **GOAL:** Implement a mandatory backup before any operation (Section VI of analysis).
      * **APPROACH:** Implement `BackupManager`.
      * **TEST_CASES:** `backup_budget(path)` successfully creates a timestamped ZIP archive of the entire `.ynab4` directory. Verify archive contents. Test error handling for invalid paths.
      * **COMPLETED:** 2025-08-31 - BackupManager class implemented with full test coverage. Creates timestamped ZIP backups with validation and error handling.
  * **TASK 0.3: (TDD) File Locking Mechanism (src/ynab_io/safety.py)** ✅ **COMPLETED**
      * **GOAL:** Prevent concurrent access and synchronization conflicts (Section VI of analysis).
      * **APPROACH:** Implement `LockManager` as a context manager, utilizing the `filelock` library for robustness.
      * **TEST_CASES:** Acquires a lock file within the `.ynab4` directory on entry. Releases the lock on exit (including during exceptions). Raises an error or times out if a lock already exists.
      * **COMPLETED:** 2025-08-31 - LockManager class implemented as context manager with full test coverage. Uses filelock library for robust concurrent access prevention with timeout handling and exception safety.

#### Phase 1: The Read Layer - Integration and Extension

  * **TASK 1.1: (TDD) Create a new YNAB parser from scratch** ✅ **COMPLETED**
      * **GOAL:** Create a new YNAB parser that can correctly parse the `Budget.yfull` and `.ydiff` files.
      * **APPROACH:** Create a new parser in `src/ynab_io/parser.py` that uses Pydantic models to represent the YNAB entities. The parser is responsible for reading the `Budget.yfull` and `.ydiff` files and creating the Pydantic models.
      * **TEST_CASES:** The parser correctly parses the `Budget.yfull` and `.ydiff` files. The final state of the budget is correct after applying the deltas.
      * **COMPLETED:** 2025-09-02 - Created a new YNAB parser from scratch using Pydantic models. The new parser correctly handles both the `Budget.yfull` snapshot and the `.ydiff` delta files. Critical bug fix implemented for device directory discovery using deviceGUID from .ydevice files. Comprehensive test suite created with 24 tests covering all functionality including error cases and edge cases. Pydantic models updated to use ConfigDict to resolve deprecation warnings.
      * **LEARNINGS:** 
        - **Dynamic Path Discovery**: Never assume fixed paths, always discover them dynamically based on the root budget directory. The .ydevice file contains the deviceGUID that must be used to locate the actual data directory.
        - **TDD Value**: Comprehensive test coverage (24 tests) revealed and validated the device discovery fix, ensuring robustness across different YNAB4 budget structures.
        - **Error Handling**: Proper error handling for malformed .ydevice files and missing directories is essential for production reliability.
  * **TASK 1.2: (TDD) Build a ynab_cli tool wrapping the functionality we built up to now (see below for already completed tasks)** ✅ **COMPLETED**
      * **GOAL:** Ensure cli gives access to all the useful methods we built up to now.
      * **APPROACH:** Use industry standard cli lib, make sure to approach it with TDD - you can use the same fixtures we already have
      * **TEST_CASES:** Validates all commands work
      * **COMPLETED:** 2025-09-02 - Implemented ynab_cli tool with Typer and full test coverage (14 tests). The CLI provides three commands: load (displays budget summary), backup (creates timestamped backups), and inspect (shows detailed account/transaction info). All commands properly integrate with LockManager for safe operations and provide comprehensive error handling. CLI tests validate both successful operations and error scenarios including lock timeouts.
      * **LEARNINGS:**
        - **CLI Integration**: Typer provides excellent command-line interface capabilities with type checking and automatic help generation.
        - **Safety First**: Integration with LockManager ensures all CLI operations are safe from concurrent access issues.
        - **Test Coverage**: Comprehensive CLI testing including mock scenarios for lock management validates real-world usage patterns.

#### Phase 2: The Write Layer - Porting `php-ynab4`

  * **TASK 2.1: Analyze `php-ynab4` Write Logic** ✅ **COMPLETED**
      * **GOAL:** Understand the precise mechanism for writing changes in YNAB4.
      * **APPROACH:** Analyze the PHP source code. Focus on: 1. Device registration. 2. "Knowledge" version tracking. 3. The JSON structure and serialization format (camelCase) of a `.ydiff`. 4. The filename convention (`<start>_<end>.ydiff`). 5. Updating the `.ydevice` file.
      * **OUTCOME:** Write a comprehensive test based on the above analysis.
      * **COMPLETED:** 2025-09-02 - Comprehensive analysis of php-ynab4 write mechanisms completed using code-archaeologist agent. Created 23 comprehensive tests covering all 5 key areas: device registration (GUID generation, .ydevice files), knowledge version tracking (A-86 format parsing/incrementing), .ydiff JSON structure (camelCase serialization), filename conventions (startVersion_endVersion.ydiff), and .ydevice file updates. Implemented minimal DeviceManager and YnabWriter classes with full test coverage. All code quality issues resolved to meet CLAUDE.md standards.
      * **LEARNINGS:**
        - **Code Archaeology Value**: The code-archaeologist agent provided precise technical specifications from php-ynab4 that would have been difficult to reverse-engineer from YNAB4 files alone. This approach saved significant research time.
        - **TDD Refinement Process**: Initial TDD implementation required code quality review and refinement. The review-fix cycle ensured production-ready code that met all CLAUDE.md standards.
        - **YNAB4 Format Complexity**: YNAB4 write operations involve intricate version tracking, device coordination, and atomic file updates. The 23 tests reveal the full complexity that must be handled.
        - **Minimal Implementation Strategy**: Starting with comprehensive tests allowed building exactly what's needed without over-engineering. The initial over-implementation had to be trimmed back to tested functionality only.
        - **Error Handling Patterns**: YNAB4 operations require graceful failure modes since budget corruption is unacceptable. Tests validated that errors return safely rather than failing hard.

  * **TASK 2.2: (TDD) Port Device Management (src/ynab_io/device_manager.py)** ✅ **COMPLETED**
      * **GOAL:** Register the tool as a valid YNAB device.
      * **APPROACH:** Port the logic from `php-ynab4`. Implement `DeviceManager`.
      * **TEST_CASES:** Generates a unique Device GUID. Creates the corresponding directory. Initializes a valid `.ydevice` file (e.g., `hasFullKnowledge: false`).
      * **COMPLETED:** 2025-09-02 - Device Management functionality fully implemented with TDD methodology. DeviceManager class provides complete device registration, GUID generation, and .ydevice file management. Key fixes applied: hasFullKnowledge correctly set to false as specified, device directory creation added to register_new_device method. All 23 tests passing with comprehensive coverage of device registration, version tracking, and file operations. Code quality review confirmed production readiness with no TODO comments, clean API design, and robust error handling.
      * **LEARNINGS:**
        - **Task Specification Precision**: Careful attention to task requirements (hasFullKnowledge: false) prevented incorrect default implementation
        - **TDD Verification Value**: Using TDD agent to verify existing implementation revealed gaps between current code and task specifications
        - **Directory Creation Pattern**: Device registration requires both .ydevice file creation AND corresponding device directory creation for complete YNAB4 integration
        - **Code Quality Review Process**: The tdd-red-green-refactor → code-quality-reviewer pipeline ensures both functional correctness and production standards adherence