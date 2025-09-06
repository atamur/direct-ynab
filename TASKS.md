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

#### Phase 2: Advanced CLI Reporting


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

  * **TASK 2.3: (TDD) Port Knowledge Management (src/ynab_io/device_manager.py)** ✅ **COMPLETED**
      * **GOAL:** Correctly track and increment the budget version.
      * **APPROACH:** Port the logic for calculating current global knowledge (by reading all `.ydevice` files) and generating the next sequential version stamp.
      * **TEST_CASES:** Correctly identifies the latest version across multiple mock devices. Generates the correct next version string.
      * **COMPLETED:** 2025-09-04 - Implemented `get_global_knowledge` in `DeviceManager` to read all `.ydevice` files and determine the latest knowledge version. Added comprehensive tests to verify the logic, including cases with multiple devices and no devices.
      * **LEARNINGS:**
        - The `get_latest_version` method with a custom sorting key is a robust way to find the latest knowledge version across multiple devices.
        - It's important to handle edge cases, such as when no `.ydevice` files are present, to prevent unexpected errors.

  * **TASK 2.4: (TDD) Port `.ydiff` Generation and Writing (src/ynab_io/writer.py)** ✅ **COMPLETED**
      * **GOAL:** Generate a valid `.ydiff` file containing the changes.
      * **APPROACH:** Implement `DeltaWriter`. Collect "dirty" entities. Serialize them into the exact JSON format (ensure camelCase serialization). Update the `entityVersion` of the modified entities during serialization. Determine the correct filename and write it to the tool's device directory.
      * **TEST_CASES:** Generates a valid JSON structure matching YNAB4 specs. Uses the correct filename. Writes the file to the correct location. Updates the `.ydevice` file after writing.
      * **COMPLETED:** 2025-09-04 - Verified the `write_changes` method in `YnabWriter` and added a comprehensive test to ensure it correctly generates a `.ydiff` file, writes it to the correct location, and updates the `.ydevice` file.
      * **LEARNINGS:**
        - The `write_changes` method provides a good foundation for the write workflow.
        - The path discovery methods in `YnabWriter` (`_get_device_info`, `_get_device_directory`, and `_get_ydevice_file_path`) are simplistic and should be refactored into a centralized path management class as suggested in **TASK 2.4: Consolidate Path Discovery Logic**.

  * **TASK 2.5: (TDD) Integration Test: Read-Modify-Write Cycle** ✅ **COMPLETED**
      * **GOAL:** Verify the end-to-end data integrity.
      * **APPROACH:** Load budget -> Modify a transaction in memory -> Write the `.ydiff` -> Read the budget again -> Verify the change is present and the structure is valid.
      * **COMPLETED:** 2025-09-04 - Implemented an integration test for the read-modify-write cycle. This test loads a budget, modifies a transaction, writes the changes to a `.ydiff` file, reads the budget again, and verifies that the changes are present. This ensures the end-to-end data integrity of the read/write operations.
      * **LEARNINGS:**
        - A full integration test is crucial for verifying the correctness of the entire read-modify-write cycle.
        - It is important to ensure that the serialization and deserialization of entities correctly handle all fields, including optional ones like `memo`.
        - The Pydantic `model_dump()` method should be used instead of the deprecated `dict()` method.

  * **TASK 2.6: Refactor `YnabParser` for Robust Path Discovery** ✅ **COMPLETED**
      * **GOAL:** Improve the parser's robustness by reading all `.ydevice` files to dynamically and accurately identify the active device and its data directory.
      * **APPROACH:** Refactor `_find_device_dir` to read all `.ydevice` files and use the information within them to correctly identify the active device and its corresponding data directory.
      * **TEST_CASES:** The parser correctly identifies the active device in a multi-device setup. The parser correctly falls back to a default device if no active device can be determined.
      * **COMPLETED:** 2025-09-04 - Enhanced DeviceManager.get_active_device_guid() to intelligently select the device with the latest knowledge version rather than alphabetical order. Added robust multi-device support with graceful fallback logic. Comprehensive test suite (4 new tests) validates multi-device scenarios, knowledge-based selection, and corrupted file handling. All 84 tests passing with zero regressions.
      * **LEARNINGS:**
        - **Knowledge-Based Selection**: Device selection should be based on knowledge version (recency of data) rather than alphabetical ordering for multi-device consistency
        - **Robust Error Handling**: Graceful handling of corrupted .ydevice files by skipping and continuing with valid ones ensures system resilience
        - **Backward Compatibility**: Enhanced functionality must maintain compatibility with single-device scenarios through proper fallback mechanisms
        - **TDD Refinement Process**: The TDD → Code Review cycle ensured both functional correctness and adherence to CLAUDE.md quality standards

#### Code Review Suggestions Implementation

  * **TASK 2.7: Consolidate Path Discovery Logic** ✅ **COMPLETED**
      * **GOAL:** Centralize all budget-related path discovery into a single `PathManager` class or within the `DeviceManager`.
      * **APPROACH:** Create a centralized `PathManager` or add methods to an existing class (like `DeviceManager`) to handle all budget-related path discovery. This would include finding the `data1~*` directory, the `devices` directory, and the specific device's data directory. All other classes would then use this single source of truth for path information.
      * **TEST_CASES:** The `PathManager` correctly finds all required paths. Other classes correctly use the `PathManager` to get path information.
      * **COMPLETED:** 2025-09-04 - Successfully consolidated all budget-related path discovery into DeviceManager class, serving as the single source of truth for all path operations. Added two new public methods: `get_devices_dir_path()` and `get_budget_file_path(device_guid)`. Refactored YnabParser to use centralized path discovery instead of manual path construction. Created comprehensive test suite with 20 tests covering all aspects of path discovery consolidation, error handling, and integration. Subsequently optimized test suite by removing 15 duplicative tests, reducing total from 104 to 89 tests while maintaining 100% functional coverage. All 89 tests pass with zero regressions.
      * **LEARNINGS:**
        - **Centralization Benefits**: Consolidating path discovery into a single class significantly improves maintainability and consistency across the codebase
        - **API Design Consistency**: Following established patterns for new methods (error handling, type hints, docstrings) creates a cohesive and predictable API
        - **Refactoring Impact**: Even small changes like consolidating path discovery can have significant positive impact on code quality and maintainability
        - **Integration Testing Value**: The 20 comprehensive tests validate not just individual methods but the entire consolidation approach, ensuring reliable path operations
        - **Code Quality Review Process**: The TDD → Code Quality Review cycle identified strengths and ensured adherence to CLAUDE.md standards
        - **Test Suite Optimization**: Removing 15 duplicative tests (75% of new tests) eliminated maintenance overhead while preserving 100% functional coverage. Comprehensive duplication analysis revealed significant overlap with existing parser, writer, and integration tests
        - **Coverage Analysis**: Existing test suites already provided robust coverage of path discovery through functional tests, making dedicated path discovery tests largely redundant

  * **TASK 2.8: Enhanced CLI Error Handling and User Feedback** ✅ **COMPLETED**
      * **GOAL:** Implement more specific error handling in `src/orchestration/cli.py` to provide users with more precise and actionable feedback.
      * **APPROACH:** Enhanced the error handling in the CLI to provide more specific and actionable error messages to the user. Caught more specific exceptions and provided tailored messages. Improved the `locked_budget_operation` context manager to provide more granular error messages about why a lock could not be acquired.
      * **TEST_CASES:** The CLI provides specific error messages for different error conditions. The `locked_budget_operation` context manager provides specific error messages for lock acquisition failures.
      * **COMPLETED:** 2025-09-05 - Enhanced CLI error handling with specific error messages for different error conditions. Improved `locked_budget_operation` context manager to handle Timeout, PermissionError, OSError (disk space), and ValueError exceptions with user-friendly messages. Updated `handle_budget_error` function to provide specific error messages for JSON parsing errors, FileNotFoundError, ValueError (corrupted data), PermissionError, and disk space errors. Fixed architectural issues by moving CLI to correct location (`src/orchestration/cli.py`) and updating all import paths. All 101 tests passing with 26 CLI tests covering enhanced error handling scenarios.
      * **LEARNINGS:**
        - **Architectural Consistency**: Proper project structure adherence is crucial - CLI belongs in `src/orchestration/` not `src/ynab_io/orchestration/` according to CLAUDE.md specifications
        - **Code Review Value**: The TDD → Code Quality Review cycle identified critical import structure issues that would have caused runtime failures
        - **Error Message Design**: User-friendly error messages with actionable feedback significantly improve user experience compared to generic exception messages
        - **Error Handling Hierarchy**: Proper exception type checking order (JSONDecodeError before ValueError) prevents incorrect error categorization
        - **Platform Independence**: Using `errno` module constants instead of hardcoded error numbers ensures cross-platform compatibility
        - **Test Coverage Impact**: Comprehensive error handling tests (26 test cases) validate all error scenarios without requiring extensive integration testing

*   **TASK 2.9: (TDD) Create Budget Calculator (src/ynab_io/budget_calculator.py)** ✅ **COMPLETED**
    *   **GOAL:** Create a `BudgetCalculator` class that takes a `Budget` object and provides calculation methods.
    *   **APPROACH:** The class will be initialized with a `Budget` object. It will contain methods for calculating account balances and monthly budget summaries.
    *   **TEST_CASES:** The `BudgetCalculator` is initialized correctly with a `Budget` object.
    *   **COMPLETED:** 2025-09-05 - Created the `BudgetCalculator` class in `src/ynab_io/budget_calculator.py` and a corresponding test file `tests/test_budget_calculator.py`. The `BudgetCalculator` is initialized with a `Budget` object. All tests pass.
    *   **LEARNINGS:**
        - Running `pytest` from the root directory is crucial for the test environment to correctly identify and import modules from the `src` directory.

*   **TASK 2.11: (TDD) Implement Monthly Budget Summary in BudgetCalculator** ✅ **COMPLETED**
    *   **GOAL:** Implement `get_monthly_budget_summary(month)` in `BudgetCalculator`.
    *   **APPROACH:** The method will take a month string (e.g., "2025-09"). It will find the corresponding `MonthlyBudget` and then, for each category, it will find the `MonthlyCategoryBudget` to get the budgeted amount. It will also iterate through all transactions in that month to calculate the total outflow for each category.
    *   **TEST_CASES:** Correctly calculates budget summaries for different months. Handles categories with no transactions. Correctly calculates outflows.
    *   **COMPLETED:** 2025-09-06 - Successfully implemented `get_monthly_budget_summary` method in `BudgetCalculator` using TDD methodology. The implementation correctly matches transactions to categories using `categoryId` field (discovered from YNAB4 fixture data). Added missing `categoryId` field to Transaction model. Fixed type annotations and improved business logic based on code quality review. All 11 tests passing including comprehensive edge case coverage.
    *   **LEARNINGS:**
        - **Data Model Discovery**: YNAB4 transactions DO contain a `categoryId` field, which was missing from the original Transaction model. Always examine actual fixture data to understand true data structure.
        - **Code Quality Review Value**: The tdd-red-green-refactor → code-quality-reviewer pipeline identified critical issues (flawed business logic, missing type annotations) that needed fixing for production-ready code.
        - **Business Logic Correctness**: Initial implementation incorrectly matched transactions by amount instead of using proper category relationships. Proper category-based matching is essential for accurate budget reporting.
        - **Type Safety**: Adding proper type annotations with `Generator` and model imports ensures type safety and catches potential runtime errors during development.

  * **TASK 2.10: (TDD) Implement Account Balance Calculation in BudgetCalculator** ✅ **COMPLETED**
      * **GOAL:** Implement `get_account_balance(account_id)` in `BudgetCalculator`.
      * **APPROACH:** The method will iterate through all transactions associated with the given `account_id`. It will sum up the `amount` of each transaction to calculate the total balance. It will also differentiate between cleared and uncleared transactions.
      * **TEST_CASES:** Correctly calculates balances for accounts with no transactions, only cleared transactions, only uncleared transactions, and a mix of both.
      * **COMPLETED:** 2025-09-05 - Implemented `get_account_balance` in `BudgetCalculator` and verified with comprehensive tests. All tests passed, and linting issues were resolved by configuring `flake8` to align with `black`'s formatting.
      * **LEARNINGS:**
        - **Linting Configuration**: It's crucial to ensure linting tools (like `flake8`) are correctly configured to match code formatters (like `black`) to avoid unnecessary conflicts. Using a `.flake8` file is a reliable way to achieve this when `pyproject.toml` integration is problematic.
        - **Automated Formatting**: Tools like `black` are invaluable for maintaining code style and reducing manual linting fixes.

  * **TASK 2.13: (TDD) Refactor CLI to use Subcommands** ✅ **COMPLETED**
      * **GOAL:** Reorganize the CLI to use a subcommand structure for better organization and scalability.
      * **APPROACH:** Create new `budget` and `accounts` subcommands. Move the existing `load` command to be `budget show`. Create `accounts list` command. Remove the `inspect` command and move its functionality to the new subcommands.
      * **TEST_CASES:** `ynab-ai budget show --budget-path <path>` runs successfully. `ynab-ai accounts list --budget-path <path>` runs successfully.
      * **COMPLETED:** 2025-09-06 - Successfully refactored CLI from individual commands to subcommand structure using TDD methodology. Implemented `budget show`, `accounts list` commands and standardized all commands to use `--budget-path` parameter. Updated all 26 existing tests to work with new subcommand structure. All 187 tests passing with 92.41% coverage. Eliminated code duplication and maintained comprehensive error handling.
      * **LEARNINGS:**
        - **Subcommand Architecture**: Typer's sub-applications provide clean separation of concerns and better CLI organization for scalable command structures
        - **Parameter Consistency**: Standardizing parameter names across all commands (`--budget-path`) creates predictable user experience and easier maintenance
        - **Test Migration Strategy**: When refactoring interfaces, updating existing tests is critical - failing tests indicate broken functionality even when new functionality works
        - **TDD → Code Quality Review Cycle**: Initial TDD implementation often requires refinement - the review-fix cycle ensures production standards are met
        - **Error Handling Preservation**: Complex error handling systems must be carefully migrated to maintain user experience during interface refactoring

 *   **TASK 2.14: (TDD) Improve CLI Output with Rich Tables** ✅ **COMPLETED**
     *   **GOAL:** Enhance the CLI output by using tables for better readability.
     *   **APPROACH:**
         1.  Integrate the `rich` library for creating tables. Introduce an output format flag
         2.  Update the `accounts list` command to display accounts in a table when format set to table.
         3.  Update the `budget show` command to display transactions in a table when format set to table.
     *   **TEST_CASES:**
         *   The `accounts list` command output is a formatted table.
         *   The `budget show` command output includes a formatted table for transactions.
     *   **COMPLETED:** 2025-09-06 - Successfully implemented Rich table functionality for CLI using TDD methodology. Added `rich>=13.0.0` dependency to pyproject.toml. Enhanced both `accounts list` and `budget show` commands with `--format` option supporting "text" (default) and "table" formats. Implemented clean table display functions using Rich's Console and Table components. All 30 tests passing including comprehensive coverage of both table and text output formats. Code quality review confirmed production-ready implementation meeting all CLAUDE.md standards.
     *   **LEARNINGS:**
         - **Rich Library Integration**: Rich provides excellent table formatting capabilities with minimal overhead and clean API design. Console and Table components offer professional-looking output enhancement.
         - **Backward Compatibility Strategy**: Adding new `--format` option with "text" default ensures existing workflows remain unchanged while providing enhanced table output as opt-in feature.
         - **TDD → Code Quality Review Value**: The TDD implementation followed by comprehensive code quality review ensures both functional correctness and production standards adherence, resulting in clean, maintainable code.
         - **CLI Enhancement Patterns**: Output format flags provide scalable approach for CLI feature enhancement - can be extended to JSON, CSV, or other formats in future.
         - **Test Coverage for UI Changes**: Testing table output requires verification of Rich-specific formatting characters (table borders) to ensure proper table rendering, not just content accuracy.

 *   **TASK 2.15: (TDD) Add `transactions` Subcommand** ✅ **COMPLETED**
     *   **GOAL:** Create a dedicated subcommand for transaction-related operations.
     *   **APPROACH:**
         1.  Create a new `transactions` subcommand.
         2.  Create a `list` command under `transactions` that displays recent transactions.
     *   **TEST_CASES:**
         *   `ynab-ai transactions list --budget-path <path>` runs successfully and displays transactions in text or table.
     *   **COMPLETED:** 2025-09-06 - Successfully implemented `transactions` subcommand using TDD methodology. Added `transactions_app` Typer subcommand group with `list` command. Follows exact patterns from existing `budget` and `accounts` subcommands including `--budget-path` and `--format` parameters. Reuses existing display functions and error handling via `locked_budget_operation` context manager. Comprehensive test suite with 7 tests covering success scenarios, format options, and error handling. All 37 CLI tests passing. Code quality review confirmed exemplary implementation meeting all CLAUDE.md standards.
     *   **LEARNINGS:**
         - **Subcommand Architecture Scalability**: Typer subcommand groups provide clean extensibility for transaction-related functionality - can easily add more transaction commands in future
         - **Code Reuse Excellence**: Leveraging existing display functions and error handling patterns eliminates duplication while maintaining consistency across all CLI commands
         - **TDD → Code Quality Review Pipeline**: The Red-Green-Refactor cycle followed by comprehensive code review ensures both functional correctness and production standards, resulting in exemplary code quality
         - **Integration Testing Value**: Using real fixture data and comprehensive error scenario testing validates the command works properly in real-world usage patterns
         - **Pattern Consistency Benefits**: Following established CLI patterns creates predictable user experience and simplified maintenance across all subcommands

