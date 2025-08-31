### YNAB4 AI Automation

### AI Agent Instructions

**TASK IMPLEMENTATION LOOP:**
Read CLAUDE.md and afterward - these instructions carefully and follow them step by step.

Use TodoWrite tool to write down all the 6 steps below before you start.

0. **Review code structure and details** - Use CLAUDE.md and LIBS.md for reference
1. **Execute tasks sequentially** - Pick with the next available task from Phase 0, 1, 2, 3, 4, or 5 and think thoroughly to plan the execution steps
2. **Follow TDD methodology** - Use tdd-red-green-refactor agent. Each task has GOAL/APPROACH/TEST_CASES structure
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

**CURRENT STATUS:** Task 1.3.2 completed. Next task: 1.4 (Extend/Wrap Data Models and Implement Change Tracking)

#### Phase 1: The Read Layer - Integration and Extension

  * **TASK 1.4: (TDD) Extend/Wrap Data Models and Implement Change Tracking (src/ynab\_io/models.py)**
      * **GOAL:** Ensure robust validation, include missing models (like `PayeeRenamingRule`), and support change tracking for the Write layer.
      * **APPROACH:** If `pynab` models are insufficient or rigid, wrap them or transition to Pydantic models. Implement a mechanism (e.g., a "dirty" flag) to track changes made to entities in memory.
      * **TEST\_CASES:** Validation catches invalid data. Modifying an attribute marks the entity as "dirty". The `PayeeRenamingRule` model is correctly defined.

  * **TASK 1.4.1: (TDD) update the cli tool to expose funcitonality added in 1.4**
      * **GOAL:** Ensure cli gives access to all the useful methods we built up to now.
      * **APPROACH:** Expand the ynab_cli tool to include the new functionality.
      * **TEST\_CASES:** Validates all commands work

#### Phase 2: The Write Layer - Porting `php-ynab4`

**Reference:** Analyze `php-ynab4` source code.

  * **TASK 2.1: Analyze `php-ynab4` Write Logic**
      * **GOAL:** Understand the precise mechanism for writing changes in YNAB4.
      * **APPROACH:** Analyze the PHP source code. Focus on: 1. Device registration. 2. "Knowledge" version tracking. 3. The JSON structure and serialization format (camelCase) of a `.ydiff`. 4. The filename convention (`<start>_<end>.ydiff`). 5. Updating the `.ydevice` file.
  * **TASK 2.2: (TDD) Port Device Management (src/ynab\_io/device\_manager.py)**
      * **GOAL:** Register the tool as a valid YNAB device.
      * **APPROACH:** Port the logic from `php-ynab4`. Implement `DeviceManager`.
      * **TEST\_CASES:** Generates a unique Device GUID. Creates the corresponding directory. Initializes a valid `.ydevice` file (e.g., `hasFullKnowledge: false`).
  * **TASK 2.3: (TDD) Port Knowledge Management (src/ynab\_io/device\_manager.py)**
      * **GOAL:** Correctly track and increment the budget version.
      * **APPROACH:** Port the logic for calculating current global knowledge (by reading all `.ydevice` files) and generating the next sequential version stamp.
      * **TEST\_CASES:** Correctly identifies the latest version across multiple mock devices. Generates the correct next version string.
  * **TASK 2.4: (TDD) Port `.ydiff` Generation and Writing (src/ynab\_io/writer.py)**
      * **GOAL:** Generate a valid `.ydiff` file containing the changes.
      * **APPROACH:** Implement `DeltaWriter`. Collect "dirty" entities. Serialize them into the exact JSON format (ensure camelCase serialization). Update the `entityVersion` of the modified entities during serialization. Determine the correct filename and write it to the tool's device directory.
      * **TEST\_CASES:** Generates a valid JSON structure matching YNAB4 specs. Uses the correct filename. Writes the file to the correct location. Updates the `.ydevice` file after writing.
  * **TASK 2.5: (TDD) Integration Test: Read-Modify-Write Cycle**
      * **GOAL:** Verify the end-to-end data integrity.
      * **APPROACH:** Load budget -\> Modify a transaction in memory -\> Write the `.ydiff` -\> Read the budget again -\> Verify the change is present and the structure is valid.

#### Phase 3: Data Transformation and AI Preparation

  * **TASK 3.1: (TDD) Transform to Tabular Format (src/categorization/transformer.py)**
      * **GOAL:** Prepare data for AI analysis (Pandas DataFrame).
      * **APPROACH:** Convert the in-memory object model (Budget State) into a DataFrame. Denormalize the data (join transactions with accounts, payees, and categories to include names, not just IDs).
      * **TEST\_CASES:** Correct mapping of fields. Handling of split transactions. Correct handling of dates and milliunits.
  * **TASK 3.2: (TDD) Feature Engineering (src/categorization/transformer.py)**
      * **GOAL:** Clean data for better AI performance.
      * **APPROACH:** Implement text cleaning for raw payee names and memos (e.g., removing store numbers, normalizing whitespace, standardizing case).
      * **TEST\_CASES:** "STARBUCKS \#1234" becomes "starbucks".

#### Phase 4: AI/LLM Integration - Hybrid Strategy

**Dependencies:** `openai` or `anthropic` (depending on LLM choice).

  * **TASK 4.1: (TDD) L1 - Deterministic Categorization (src/categorization/engine.py)**
      * **GOAL:** Apply high-confidence historical matching before using LLMs.
      * **APPROACH:** Analyze the historical DataFrame. Implement logic to find the most frequent category for a given payee if the consistency is high (e.g., \>95%).
      * **TEST\_CASES:** Correctly identifies high-confidence matches. Ignores low-confidence matches.
  * **TASK 4.2: (TDD) L2 - LLM Client and Prompt Engineering (src/categorization/llm\_client.py)**
      * **GOAL:** Use LLMs to categorize ambiguous or new transactions.
      * **APPROACH:** Implement `LLMClient`. Design precise prompts including: Transaction details, the user's full category hierarchy, and *few-shot examples* dynamically selected from the user's history. Instruct the LLM to return structured JSON (`NormalizedPayeeName`, `PredictedCategoryName`).
      * **TEST\_CASES:** Prompt generation is correct. Mock LLM API calls. Response parsing and validation handle structured JSON and potential LLM errors.
  * **TASK 4.3: (TDD) Payee Standardization and Rule Creation (src/categorization/engine.py)**
      * **GOAL:** Clean up payee names and create YNAB rules for future imports.
      * **APPROACH:** Process the `NormalizedPayeeName`. Find the existing Payee entity or create a new one. **Crucially**, create a new `PayeeRenamingRule` entity (using the model from Task 1.4) mapping the raw input payee to the standardized payee.
      * **TEST\_CASES:** Correctly creates/finds standardized Payee. Generates a valid `PayeeRenamingRule` object.
  * **TASK 4.4: (TDD) Categorization Pipeline (src/categorization/engine.py)**
      * **GOAL:** Combine L1 and L2 logic and apply changes to the in-memory state.
      * **APPROACH:** Implement the workflow (L1 -\> L2). Update the `Transaction`, `Payee`, and `PayeeRenamingRule` objects in memory. Ensure these objects are marked as "dirty" (Task 1.4).
      * **TEST\_CASES:** End-to-end categorization test on a list of uncategorized transactions.

#### Phase 5: Workflow Orchestration and Safety Simulation

  * **TASK 5.1: (TDD) Implement Budget Simulator (src/simulation/simulator.py)**
      * **GOAL:** Mitigate the "Temporal Ripple Effect" (Section VI of analysis).
      * **APPROACH:** Implement `ChangeSimulator`. Apply proposed changes in a sandboxed memory state. Implement basic YNAB logic (category rollover, "To Be Budgeted" calculation) to recalculate the state for the affected month and *all subsequent months* to detect downstream impacts.
      * **TEST\_CASES:** Detects if a change causes a negative "To Be Budgeted" or uncovered overspending in the current or future months.
  * **TASK 5.2: (TDD) Full Workflow Orchestration (src/orchestration/workflow.py)**
      * **GOAL:** Combine all phases into a safe, sequential workflow.
      * **APPROACH:** Implement the master workflow: Lock -\> Backup -\> Load -\> Analyze/Predict -\> Simulate -\> Review (CLI output) -\> Save (if confirmed) -\> Unlock.
  * **TASK 5.3: (TDD) CLI and Dry Run (src/orchestration/cli.py)**
      * **GOAL:** Provide a user interface and safety check.
      * **APPROACH:** Implement CLI (e.g., using `Typer` or `argparse`). Command: `ynab-ai categorize --budget-path <path> [--dry-run]`. Implement interactive confirmation showing proposed changes AND simulation results.
      * **TEST\_CASES:** Dry run executes the full pipeline but does not write files. Confirmation prompt correctly gates the write operation.
  * **TASK 5.4: Logging and Error Handling**
      * **GOAL:** Ensure robustness and traceability.
      * **APPROACH:** Implement comprehensive logging throughout the application. Ensure robust error handling that guarantees the lock is always released, even if the process fails.

### AI Agent Task Backlog : TASKS DONE

#### Phase 0: Project Setup and Safety Protocols

  * **TASK 0.1: Environment Initialization** ✅ **COMPLETED**
      * **GOAL:** Set up the project structure and testing framework.
      * **APPROACH:** Initialize the directory structure as defined above, configure `pyproject.toml`, and set up `pytest`.
      * **COMPLETED:** 2025-08-31 - Project structure created, pyproject.toml configured with all dependencies, pytest framework installed and verified with passing tests.
  * **TASK 0.2: (TDD) Backup Utility (src/ynab\_io/safety.py)** ✅ **COMPLETED**
      * **GOAL:** Implement a mandatory backup before any operation (Section VI of analysis).
      * **APPROACH:** Implement `BackupManager`.
      * **TEST\_CASES:** `backup_budget(path)` successfully creates a timestamped ZIP archive of the entire `.ynab4` directory. Verify archive contents. Test error handling for invalid paths.
      * **COMPLETED:** 2025-08-31 - BackupManager class implemented with full test coverage. Creates timestamped ZIP backups with validation and error handling.
  * **TASK 0.3: (TDD) File Locking Mechanism (src/ynab\_io/safety.py)** ✅ **COMPLETED**
      * **GOAL:** Prevent concurrent access and synchronization conflicts (Section VI of analysis).
      * **APPROACH:** Implement `LockManager` as a context manager, utilizing the `filelock` library for robustness.
      * **TEST\_CASES:** Acquires a lock file within the `.ynab4` directory on entry. Releases the lock on exit (including during exceptions). Raises an error or times out if a lock already exists.
      * **COMPLETED:** 2025-08-31 - LockManager class implemented as context manager with full test coverage. Uses filelock library for robust concurrent access prevention with timeout handling and exception safety.

#### Phase 1: The Read Layer - Integration and Extension

  * **TASK 1.1: Analyze `pynab` Capabilities and Models** ✅ **COMPLETED**
      * **GOAL:** Understand `pynab`'s functionality and limitations.
      * **APPROACH:** Review the `pynab` source code. 1. Does it only read `Budget.yfull` or does it process `.ydiff` files? (Analysis suggests it likely only reads the snapshot). 2. How complete are its data models? Specifically check for `PayeeRenamingRule` (essential for the goal), `entityVersion`, and `isTombstone`.
      * **COMPLETED:** 2025-08-31 - Full analysis documented in LIBS.md. Key findings: pynab only reads Budget.yfull (no .ydiff support), all required models present (PayeeRenamingRule = PayeeRenameConditions).
  * **TASK 1.2: (TDD) Integrate `pynab` Reader (src/ynab\_io/reader.py)** ✅ **COMPLETED**
      * **GOAL:** Use `pynab` to load the initial budget snapshot.
      * **APPROACH:** Implement `BudgetReader` that wraps `pynab`'s loading functionality. Ensure it locates the data folder via `Budget.ymeta`.
      * **TEST\_CASES:** Successfully loads the mock `Budget.yfull`. Verify the structure and counts of key entities.
      * **COMPLETED:** 2025-08-31 - BudgetReader class implemented with full test coverage. Enhanced with real fixture tests (18 tests total). **Implementation Details:**
        - **Python 3.12 Compatibility**: Added monkey patch for collections.abc (lines 10-19 in reader.py)  
        - **Device Selection Limitation**: pynab YNAB constructor lacks device_guid support - documented in LIBS.md
        - **Attribute Naming**: pynab uses `transaction.account/payee` not `account_id/payee_id` - tests updated accordingly
        - **Real Fixture Integration**: Added tests using "My Test Budget~E0C1460F.ynab4" fixture for comprehensive validation
        - **Error Handling**: Graceful fallbacks for unsupported parameters and invalid paths
  * **TASK 1.3: (TDD) Implement Delta Application Logic (Crucial Extension)** ✅ **COMPLETED**
      * **GOAL:** Reconstruct the current state by applying `.ydiff` files (Section II of analysis).
      * **APPROACH:** Extend `BudgetReader`. Implement logic to discover, sort (chronologically by version stamp), and apply `.ydiff` files to the base state loaded by `pynab`.
      * **TEST\_CASES:** Load a budget with a snapshot and subsequent diffs. Verify the final state reflects the changes, respecting `entityVersion` precedence and `isTombstone` deletions.
      * **COMPLETED:** 2025-08-31 - Delta application logic implemented with TDD methodology. Added 6 comprehensive tests using real YNAB4 fixture. Includes delta discovery, chronological sorting, version parsing, and framework for entity version/tombstone handling. All 15 reader tests passing. Code quality review approved.
  * **TASK 1.3.1: Carefully review the provided YNAB fixture file and existing reader tests; then propose TASK 1.3.1.1 with the goal to cover the fixture test with real assertions based on the data** ✅ **COMPLETED**
      * **GOAL:** Ensure our tests are validating real fixtures behavior
      * **APPROACH:** Reading plain text files from fixture should give you an idea of what the data looks like.
      * **COMPLETED:** 2025-08-31 - Analyzed fixture structure ("My Test Budget~E0C1460F.ynab4") containing 1 account, 29 categories, 4 payees, 3 transactions, and 4 delta files. Key findings: transaction ID 44B1567B-7356-48BC-1D3E-FFAED8CD0F8C evolves from amount 0→20000 through deltas. Proposed TASK 1.3.1.1 with 10 specific test cases covering exact entity counts, referential integrity, and delta evolution validation.
  * **TASK 1.3.1.1: (TDD) Enhanced Fixture Tests with Real Data Assertions** ✅ **COMPLETED**
      * **GOAL:** Replace generic fixture tests with specific assertions based on actual fixture data to ensure our reader correctly parses real YNAB4 budget structure and content.
      * **APPROACH:** 1. Add comprehensive tests that validate specific entities from the "My Test Budget~E0C1460F.ynab4" fixture. 2. Test exact counts, names, IDs, and relationships from the fixture data. 3. Validate key transaction data evolution through delta files. 4. Ensure payee, account, and category data integrity with real fixture values.
      * **TEST_CASES:** Exact Entity Counts (1 account, 29 categories, 4 payees, 3 transactions). Account Validation ("Current" account with ID). Master Category Structure (6 master categories). Specific Category Tests ("Tithing", "Charitable" under "Giving"). Payee Data Integrity ("Starting Balance", "Migros", "Salary"). Transaction Evolution (amount 0→20000). Delta File Validation (4 files). Entity Version Tracking (A-66→A-72). Account-Payee-Transaction Relationships. Category Hierarchy.
      * **COMPLETED:** 2025-08-31 - Enhanced fixture tests implemented with TDD methodology. Added comprehensive TestBudgetReaderRealDataAssertions class with 10 specific test methods validating exact fixture data. **Implementation Details:**
        - **Complete Test Coverage**: All 10 test cases implemented covering entity counts, relationships, and data integrity
        - **Real Data Validation**: Tests validate specific IDs, names, and values from actual fixture ("Current" account, "Tithing"/"Charitable" categories, transaction evolution)
        - **Comprehensive Assertions**: 42 total tests passing, including 10 new fixture-specific tests with detailed error messages
        - **Code Quality**: Clean implementation with helper methods, comprehensive docstrings, and no TODO comments
        - **TDD Methodology**: Strict Red-Green-Refactor cycle followed with failing tests first, minimal implementation, then refactoring for quality
  * **TASK 1.3.2: (TDD) Build a ynab_cli tool wrapping the functionality we built up to now (see below for already completed tasks)**
      * **GOAL:** Ensure cli gives access to all the useful methods we built up to now.
      * **APPROACH:** Use industry standard cli lib, make sure to approach it with TDD - you can use the same fixtures we already have
      * **TEST\_CASES:** Validates all commands work
- 