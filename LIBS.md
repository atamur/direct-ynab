# External Libraries Analysis

This document contains detailed analysis of external libraries and their capabilities for the direct-ynab project.

## Library Analysis Template

When analyzing new external libraries, use this template to ensure consistency:

```markdown
## LibraryName (vX.X.X)

**Repository**: https://github.com/user/repo
**Installation**: `pip install library-name` or `pip install git+https://...`
**Status**: ✅ Installed and Added to pyproject.toml

### Overview
Brief description of what the library does and its primary purpose.

### Key Capabilities
1. **Feature 1**: Description
2. **Feature 2**: Description
3. **Feature 3**: Description

### Critical Limitations
❌ **Limitation 1**: Description of what it cannot do
❌ **Limitation 2**: Another important limitation

### Data Model/API Completeness
✅/❌ **Required Feature**: Present/Missing details

### Integration Strategy
1. ✅ **Use for**: What we should use it for
2. ⚠️ **Extend for**: What we need to add/extend
3. ❌ **Avoid**: What we should not use it for

### Next Steps
- Task references and implementation notes
```

## pynab (v0.6.8)

**Repository**: https://github.com/aldanor/pynab  
**Installation**: `pip install git+https://github.com/aldanor/pynab.git`  
**Status**: ✅ Installed and Added to pyproject.toml

### Overview

pynab is a Python library for reading YNAB4 budget files. It provides object-oriented access to budget data with filtering, querying, and navigation capabilities.

### Key Capabilities

1. **Budget Loading**: Loads YNAB4 budgets from `.ynab4` directories via `Budget.ymeta`
2. **Device Selection**: Automatically selects device with latest modification time or allows manual selection
3. **Data Models**: Complete object model for all YNAB entities (Accounts, Payees, Categories, Transactions, etc.)
4. **Collections**: Rich collection classes with filtering, sorting, and indexing
5. **Data Validation**: Uses Schematics library for robust data validation

### Critical Limitations

❌ **NO .ydiff Processing**: pynab only reads `Budget.yfull` snapshot files. It does NOT process `.ydiff` delta files.
- Line 51 in `ynab.py`: `budget_file = os.path.join(data_folder, guid, 'Budget.yfull')`
- No delta application logic exists anywhere in the codebase

❌ **No Device Selection Support**: pynab YNAB constructor does not support `device_guid` parameter.
- Constructor signature: `YNAB(budget_dir, budget_name)` only
- Device selection happens automatically (latest modification time)
- Cannot specify particular device GUID for loading specific device data

❌ **Python 3.12+ Compatibility Issue**: pynab uses deprecated `collections.Sequence` (moved to `collections.abc` in Python 3.10+)
- Requires monkey patching in consuming code: `collections.Sequence = collections.abc.Sequence`
- See `src/ynab_io/reader.py:10-19` for workaround implementation
- Issue affects all collection types: `Sequence`, `MutableSequence`, `Mapping`, `MutableMapping`

❌ **Transaction Attribute Naming**: pynab uses different attribute names than expected YNAB4 schema
- Uses `transaction.account` instead of `transaction.account_id`  
- Uses `transaction.payee` instead of `transaction.payee_id`
- Attribute objects are full entity references, not just IDs

### Data Model Completeness

✅ **All Required Models Present**:

| Required Entity | pynab Model | Status | Notes |
|----------------|-------------|---------|--------|
| `entityVersion` | `Entity.entityVersion` | ✅ Present | Base entity field (schema.py:26) |
| `isTombstone` | `DeletableEntity.isTombstone` | ✅ Present | Used in `Model.is_valid` (models.py:57) |
| `PayeeRenamingRule` | `PayeeRenameConditions` | ✅ Present | Functionally equivalent (schema.py:85-89) |

#### PayeeRenameConditions Details

```python
class PayeeRenameConditions(DeletableEntity):
    parentPayeeId = StringType()    # Links to standardized payee
    operand = StringType()          # Raw/original payee name text  
    operator = StringType()         # Matching rule (equals, contains, etc.)
```

Attached to `Payee` objects via `renameConditions` list. This provides the exact functionality needed for payee standardization rules.

### Architecture

- **Base Class**: `Model` with `_entity_type` mapping to Schematics schemas
- **Collections**: `ModelCollection` subclasses with filtering and indexing
- **Entity Hierarchy**: `Entity` → `DeletableEntity` → specific models
- **Validation**: Schematics models handle JSON schema validation

### Integration Strategy

1. **✅ Use for Budget.yfull loading**: Leverage existing robust loading logic
2. **⚠️ Extend for .ydiff processing**: Must implement delta application ourselves
3. **⚠️ Add change tracking**: Need "dirty" flags for write operations
4. **✅ Reuse models**: Existing models are sufficient for our needs

### Code Examples

```python
# Basic usage
from ynab import YNAB
budget = YNAB('/path/to/budgets', 'BudgetName')

# Access data
accounts = budget.accounts
transactions = budget.transactions.filter('account', accounts['Checking'])

# Filtering and querying
recent = budget.transactions.since('30 days ago')
cleared = budget.transactions.filter('cleared')
```

### Next Steps

- ✅ **Task 1.1 Complete**: Analysis finished
- 📋 **Task 1.2**: Wrap pynab in `BudgetReader` class
- 📋 **Task 1.3**: Implement `.ydiff` delta application logic  
- 📋 **Task 1.4**: Add change tracking for write operations