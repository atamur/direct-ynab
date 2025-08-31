"""Backup and safety utilities for YNAB4 operations."""

import zipfile
from pathlib import Path
from datetime import datetime
from typing import Union


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