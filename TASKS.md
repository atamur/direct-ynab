### YNAB4 AI Automation

### AI Agent Task Backlog : IN PROGRESS

**TASK IMPLEMENTATION LOOP:**
1. **Execute tasks sequentially** - Pick with the next available task from Phase 0, 1, 2, 3, 4, or 5 and think thoroughly to plan the execuition steps
2. **Follow TDD methodology** - Each task has GOAL/APPROACH/TEST_CASES structure
3. **Use TodoWrite tool** - Track progress with todo lists for complex tasks
4. **Write tests first** - For TDD tasks, create failing tests before implementation
5. **Implement solution** - Write the minimal code to make tests pass
6. **Verify completion** - Run all tests to ensure nothing breaks
7. **Review the code diff** - Review the changes made to the code and make sure they are correct, if any feedback send it back to step (3). 
8. **Mark task complete** - Move completed task to "TASKS DONE" section

**CURRENT STATUS:** Task 0.3 completed. Next task: 1.1 (Analyze pynab Capabilities and Models)

#### Phase 1: The Read Layer - Integration and Extension

**Dependencies:** `pynab` (Agent should install this: `pip install git+https://github.com/aldanor/pynab.git` or vendor it if installation fails).

  * **TASK 1.1: Analyze `pynab` Capabilities and Models**
      * **GOAL:** Understand `pynab`'s functionality and limitations.
      * **APPROACH:** Review the `pynab` source code. 1. Does it only read `Budget.yfull` or does it process `.ydiff` files? (Analysis suggests it likely only reads the snapshot). 2. How complete are its data models? Specifically check for `PayeeRenamingRule` (essential for the goal), `entityVersion`, and `isTombstone`.
  * **TASK 1.2: (TDD) Integrate `pynab` Reader (src/ynab\_io/reader.py)**
      * **GOAL:** Use `pynab` to load the initial budget snapshot.
      * **APPROACH:** Implement `BudgetReader` that wraps `pynab`'s loading functionality. Ensure it locates the data folder via `Budget.ymeta`.
      * **TEST\_CASES:** Successfully loads the mock `Budget.yfull`. Verify the structure and counts of key entities.
  * **TASK 1.3: (TDD) Implement Delta Application Logic (Crucial Extension)**
      * **GOAL:** Reconstruct the current state by applying `.ydiff` files (Section II of analysis).
      * **APPROACH:** Extend `BudgetReader`. Implement logic to discover, sort (chronologically by version stamp), and apply `.ydiff` files to the base state loaded by `pynab`.
      * **TEST\_CASES:** Load a budget with a snapshot and subsequent diffs. Verify the final state reflects the changes, respecting `entityVersion` precedence and `isTombstone` deletions.
  * **TASK 1.4: (TDD) Extend/Wrap Data Models and Implement Change Tracking (src/ynab\_io/models.py)**
      * **GOAL:** Ensure robust validation, include missing models (like `PayeeRenamingRule`), and support change tracking for the Write layer.
      * **APPROACH:** If `pynab` models are insufficient or rigid, wrap them or transition to Pydantic models. Implement a mechanism (e.g., a "dirty" flag) to track changes made to entities in memory.
      * **TEST\_CASES:** Validation catches invalid data. Modifying an attribute marks the entity as "dirty". The `PayeeRenamingRule` model is correctly defined.

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