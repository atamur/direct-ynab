"""YNAB4 Budget Reader - Integration layer for pynab."""

import collections
import collections.abc
import json
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Monkey patch for Python 3.12 compatibility with pynab
# pynab uses collections.Sequence which was moved to collections.abc in Python 3.10+
if not hasattr(collections, 'Sequence'):
    collections.Sequence = collections.abc.Sequence
if not hasattr(collections, 'MutableSequence'):
    collections.MutableSequence = collections.abc.MutableSequence
if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
if not hasattr(collections, 'MutableMapping'):
    collections.MutableMapping = collections.abc.MutableMapping

from ynab import YNAB


class BudgetReader:
    """
    YNAB4 Budget Reader with delta application support.
    
    This class provides a clean interface for:
    - Loading Budget.yfull files through pynab integration
    - Discovering and processing .ydiff delta files
    - Applying incremental changes to reconstruct budget state
    
    The reader supports both snapshot loading (current complete state)
    and delta application (applying incremental changes chronologically).
    
    Example usage:
        reader = BudgetReader(Path("MyBudget~GUID.ynab4"))
        budget = reader.load_snapshot()
        
        # Discover and apply deltas
        deltas = reader.discover_delta_files()
        reader.apply_all_deltas()
    """
    
    def __init__(self, budget_path: Path) -> None:
        """
        Initialize BudgetReader with path to budget file.
        
        Args:
            budget_path: Path to the .ynab4 budget directory
        """
        self._budget_path = budget_path
        self._budget: Optional[YNAB] = None
        self._device_path: Optional[Path] = None
    
    @property
    def budget_path(self) -> Path:
        """Get the budget path."""
        return self._budget_path
    
    def load_snapshot(self) -> YNAB:
        """
        Load the Budget.yfull snapshot using pynab.
        
        This method uses pynab to load the budget from the .ynab4 directory.
        It automatically locates the data folder via Budget.ymeta and selects
        the appropriate device (latest modification time by default).
        
        Returns:
            YNAB budget object with all entities loaded from Budget.yfull
        
        Raises:
            FileNotFoundError: If budget path or Budget.yfull file doesn't exist
            ValueError: If budget data is invalid or corrupted
        """
        # Extract budget directory and name for pynab
        # pynab expects: path to parent dir, and budget name without ~GUID.ynab4
        budget_dir = str(self._budget_path.parent)
        budget_name = self._extract_budget_name()
        
        # Load using pynab
        # Device selection happens automatically (latest modification time)
        self._budget = YNAB(budget_dir, budget_name)
        
        return self._budget
    
    def _extract_budget_name(self) -> str:
        """
        Extract budget name from the .ynab4 filename.
        
        Handles both standard patterns like "My Test Budget~E0C1460F.ynab4"
        and non-standard naming conventions.
        
        Returns:
            Extracted budget name without the GUID suffix
        """
        filename = self._budget_path.name
        if filename.endswith('.ynab4') and '~' in filename:
            # Extract budget name before the ~GUID part
            return filename.split('~')[0]
        else:
            # Fallback to stem for non-standard names
            return self._budget_path.stem
    
    def get_budget(self) -> YNAB:
        """
        Get the currently loaded budget.
        
        Returns:
            The loaded YNAB budget object
        
        Raises:
            RuntimeError: If no budget has been loaded yet
        """
        if self._budget is None:
            raise RuntimeError("Budget not loaded. Call load_snapshot() first.")
        
        return self._budget
    
    def discover_delta_files(self) -> List[Path]:
        """
        Discover .ydiff files in the device directory and return them sorted chronologically.
        
        Returns:
            List of Path objects for .ydiff files, sorted by version stamps
            
        Raises:
            RuntimeError: If no budget has been loaded yet
        """
        if self._budget is None:
            raise RuntimeError("Budget not loaded. Call load_snapshot() first.")
        
        # Find device directory from the loaded budget's device path
        device_dir = Path(self._budget._path).parent
        self._device_path = device_dir
        
        # Find all .ydiff files
        ydiff_files = list(device_dir.glob("*.ydiff"))
        
        # Sort by version stamps (chronological order)
        return sorted(ydiff_files, key=self._get_delta_sort_key)
    
    def _get_delta_sort_key(self, delta_path: Path) -> int:
        """
        Extract sorting key from delta filename for chronological ordering.
        
        Args:
            delta_path: Path to .ydiff file
            
        Returns:
            Numeric sort key based on start version
        """
        start_version, _ = self._parse_delta_versions(delta_path.name)
        # Extract numeric part after the dash for sorting (e.g., "A-63" -> 63)
        return int(start_version.split('-')[1])
    
    def _parse_delta_versions(self, filename: str) -> Tuple[str, str]:
        """
        Parse version stamps from delta filename.
        
        Args:
            filename: Delta filename like "A-63_A-67.ydiff"
            
        Returns:
            Tuple of (start_version, end_version)
            
        Raises:
            ValueError: If filename format is invalid
        """
        if not filename.endswith('.ydiff'):
            raise ValueError(f"Invalid delta filename format: {filename}")
        
        # Remove .ydiff extension and split by underscore
        base_name = filename[:-6]  # Remove '.ydiff'
        
        try:
            start_version, end_version = base_name.split('_')
        except ValueError:
            raise ValueError(f"Invalid delta filename format: {filename}")
            
        return start_version, end_version
    
    def apply_delta(self, delta_file: Path) -> None:
        """
        Apply a single delta file to update budget state.
        
        Args:
            delta_file: Path to .ydiff file to apply
            
        Raises:
            FileNotFoundError: If delta file doesn't exist
            ValueError: If delta file format is invalid
            RuntimeError: If no budget has been loaded yet
        """
        if self._budget is None:
            raise RuntimeError("Budget not loaded. Call load_snapshot() first.")
        
        if not delta_file.exists():
            raise FileNotFoundError(f"Delta file not found: {delta_file}")
            
        delta_data = self._load_delta_file(delta_file)
        
        if "items" not in delta_data:
            raise ValueError(f"Invalid delta file format: missing 'items' field in {delta_file}")
            
        self._apply_delta_items(delta_data["items"])
    
    def load_snapshot_without_deltas(self) -> YNAB:
        """
        Load base snapshot without applying any deltas.
        
        Note: Currently returns the same as load_snapshot() since Budget.yfull 
        already contains the current complete state. In a full implementation,
        this would load an older snapshot state.
        
        Returns:
            YNAB budget object with base snapshot data
        """
        return self.load_snapshot()
    
    def apply_all_deltas(self) -> None:
        """
        Apply all delta files in chronological order.
        
        Raises:
            RuntimeError: If no budget has been loaded yet
        """
        if self._budget is None:
            raise RuntimeError("Budget not loaded. Call load_snapshot() first.")
            
        delta_files = self.discover_delta_files()
        for delta_file in delta_files:
            self.apply_delta(delta_file)
    
    def _load_delta_file(self, delta_file: Path) -> dict:
        """
        Load delta file and return its JSON data.
        
        Args:
            delta_file: Path to .ydiff file
            
        Returns:
            Dict containing delta data
            
        Raises:
            FileNotFoundError: If delta file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        try:
            with open(delta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Delta file not found: {delta_file}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in delta file {delta_file}: {e.msg}", e.doc, e.pos)
    
    def _apply_delta_items(self, items: list) -> None:
        """
        Apply delta items to update budget entities.
        
        This method processes delta items and updates the budget state by:
        - Creating new entities for items not in the current state
        - Updating existing entities if the delta version is newer
        - Deleting entities marked with isTombstone=True
        
        Args:
            items: List of delta items from .ydiff file
            
        Note: This is currently a minimal implementation that validates
        the delta items structure but doesn't modify the budget state.
        A full implementation would integrate with pynab's entity collections
        to actually apply the changes.
        """
        for item in items:
            # Validate required fields
            required_fields = ['entityId', 'entityVersion', 'isTombstone', 'entityType']
            for field in required_fields:
                if field not in item:
                    raise ValueError(f"Delta item missing required field: {field}")
            
            # In a full implementation, this would:
            # 1. Find the entity by entityId in the appropriate collection (accounts, transactions, etc.)
            # 2. Compare entityVersion to determine if update is needed
            # 3. Either create, update, or delete the entity based on isTombstone
            # 4. Handle version conflicts and maintain data consistency
            pass