"""Backup and safety utilities for YNAB4 operations."""

import zipfile
from pathlib import Path
from datetime import datetime
from typing import Union
from filelock import FileLock


class BackupManager:
    """Manages backup operations for YNAB4 budget files."""
    
    def backup_budget(self, budget_path: Union[str, Path]) -> Path:
        """
        Create a timestamped ZIP backup of a YNAB4 budget directory.
        
        Args:
            budget_path: Path to the .ynab4 budget directory
            
        Returns:
            Path to the created backup ZIP file
            
        Raises:
            FileNotFoundError: If the budget path doesn't exist
            ValueError: If the path is not a valid YNAB4 budget directory
        """
        budget_path = Path(budget_path)
        
        # Verify the budget path exists
        if not budget_path.exists():
            raise FileNotFoundError(f"Budget path does not exist: {budget_path}")
        
        # Verify it's a directory
        if not budget_path.is_dir():
            raise ValueError("Budget path must be a directory")
        
        # Verify it's a YNAB4 budget directory (contains Budget.ymeta)
        if not (budget_path / "Budget.ymeta").exists():
            raise ValueError("Not a valid YNAB4 budget directory: missing Budget.ymeta")
        
        # Generate timestamp for backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create backup filename
        budget_name = budget_path.stem  # Gets name without .ynab4 extension
        backup_filename = f"{budget_name}_backup_{timestamp}.zip"
        backup_path = budget_path.parent / backup_filename
        
        # Create the ZIP archive
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Walk through all files in the budget directory
            for file_path in budget_path.rglob('*'):
                if file_path.is_file():
                    # Calculate relative path for the archive
                    arcname = file_path.relative_to(budget_path.parent)
                    zip_file.write(file_path, arcname)
        
        return backup_path


class LockManager:
    """Manages file locking for YNAB4 budget operations to prevent concurrent access."""
    
    def __init__(self, budget_path: Union[str, Path], timeout: float = 10.0):
        """
        Initialize the LockManager.
        
        Args:
            budget_path: Path to the .ynab4 budget directory
            timeout: Timeout in seconds for acquiring the lock
            
        Raises:
            FileNotFoundError: If the budget path doesn't exist
            ValueError: If the path is not a valid YNAB4 budget directory
        """
        self.budget_path = Path(budget_path)
        self.timeout = timeout
        
        # Verify the budget path exists
        if not self.budget_path.exists():
            raise FileNotFoundError(f"Budget path does not exist: {self.budget_path}")
        
        # Verify it's a directory
        if not self.budget_path.is_dir():
            raise ValueError("Budget path must be a directory")
        
        # Verify it's a YNAB4 budget directory (contains Budget.ymeta)
        if not (self.budget_path / "Budget.ymeta").exists():
            raise ValueError("Not a valid YNAB4 budget directory: missing Budget.ymeta")
        
        # Create lock file path within the .ynab4 directory
        self.lock_file_path = self.budget_path / "budget.lock"
        self.file_lock = FileLock(str(self.lock_file_path), timeout=self.timeout)
    
    def __enter__(self):
        """Acquire the lock when entering the context manager."""
        try:
            self.file_lock.acquire()
            return self
        except Exception as e:
            raise Exception(f"Failed to acquire lock for budget: {e}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock when exiting the context manager."""
        try:
            self.file_lock.release()
        except Exception:
            # Ensure lock is always released even if an error occurs
            pass