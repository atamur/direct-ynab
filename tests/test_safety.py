"""Tests for backup and safety utilities."""

import pytest
import tempfile
import shutil
from pathlib import Path
import zipfile
from datetime import datetime
from unittest.mock import patch

from src.ynab_io.safety import BackupManager


class TestBackupManager:
    """Test cases for BackupManager class."""
    
    def setup_method(self):
        """Set up test fixtures before each test."""
        # Create a temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create a mock .ynab4 budget structure
        self.budget_dir = self.temp_dir / "TestBudget.ynab4"
        self.budget_dir.mkdir()
        
        # Create some mock files and subdirectories
        (self.budget_dir / "Budget.ymeta").write_text('{"relativeDataFolderName": "TestBudget~12345.ynab4"}')
        
        data_dir = self.budget_dir / "TestBudget~12345.ynab4"
        data_dir.mkdir()
        
        (data_dir / "Budget.yfull").write_text('{"fileMetaData": {"budgetDataVersion": "4.2"}}')
        (data_dir / "devices").mkdir()
        (data_dir / "devices" / "A").mkdir(parents=True)
        (data_dir / "devices" / "A" / "Budget.ydiff").write_text('{"changes": []}')
        
        self.backup_manager = BackupManager()
    
    def teardown_method(self):
        """Clean up test fixtures after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_backup_budget_creates_timestamped_zip(self):
        """Test that backup_budget creates a timestamped ZIP archive."""
        with patch('src.ynab_io.safety.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20230831_143022"
            
            backup_path = self.backup_manager.backup_budget(self.budget_dir)
            
            # Verify the backup file was created
            assert backup_path.exists()
            assert backup_path.suffix == '.zip'
            assert "TestBudget_backup_20230831_143022.zip" in str(backup_path)
    
    def test_backup_budget_contains_correct_files(self):
        """Test that the backup archive contains all the budget files."""
        backup_path = self.backup_manager.backup_budget(self.budget_dir)
        
        # Verify the zip file contains expected files
        with zipfile.ZipFile(backup_path, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Check that key files are present
            assert any("Budget.ymeta" in file for file in file_list)
            assert any("Budget.yfull" in file for file in file_list)
            assert any("devices/" in file for file in file_list)
    
    def test_backup_budget_raises_error_for_invalid_path(self):
        """Test that backup_budget raises an error for invalid paths."""
        invalid_path = Path("/non/existent/path.ynab4")
        
        with pytest.raises(FileNotFoundError):
            self.backup_manager.backup_budget(invalid_path)
    
    def test_backup_budget_raises_error_for_non_ynab4_directory(self):
        """Test that backup_budget raises an error for non-YNAB4 directories."""
        non_budget_dir = self.temp_dir / "NotABudget"
        non_budget_dir.mkdir()
        
        with pytest.raises(ValueError, match="Not a valid YNAB4 budget directory"):
            self.backup_manager.backup_budget(non_budget_dir)
    
    def test_backup_budget_creates_backup_in_parent_directory(self):
        """Test that backup file is created in the parent directory of the budget."""
        backup_path = self.backup_manager.backup_budget(self.budget_dir)
        
        # Verify backup is in the parent directory
        assert backup_path.parent == self.budget_dir.parent
        
    def test_backup_budget_returns_path_object(self):
        """Test that backup_budget returns a Path object."""
        backup_path = self.backup_manager.backup_budget(self.budget_dir)
        
        assert isinstance(backup_path, Path)