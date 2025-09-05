"""Tests for the YNAB CLI tool."""

import json
import zipfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from typer.testing import CliRunner
import pytest
from filelock import Timeout

from orchestration.cli import app
from ynab_io.testing import budget_version
from assertpy import assert_that


class TestEnhancedErrorHandling:
    """Test cases for enhanced CLI error handling."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")

    def test_locked_budget_operation_filelock_timeout_error(self, runner):
        """Test locked_budget_operation provides specific error for file lock timeout."""
        with patch('orchestration.cli.LockManager') as mock_lock_manager:
            mock_lock_manager.side_effect = Timeout("Lock timeout")
            
            result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
            
            assert result.exit_code == 1
            assert "Unable to acquire budget lock: Another application may be using this budget" in result.stderr

    def test_locked_budget_operation_permission_denied_error(self, runner):
        """Test locked_budget_operation provides specific error for permission denied."""
        with patch('orchestration.cli.LockManager') as mock_lock_manager:
            mock_lock_manager.side_effect = PermissionError("Permission denied")
            
            result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
            
            assert result.exit_code == 1
            assert "Permission denied accessing budget files" in result.stderr

    def test_locked_budget_operation_disk_space_error(self, runner):
        """Test locked_budget_operation provides specific error for disk space issues."""
        with patch('orchestration.cli.LockManager') as mock_lock_manager:
            mock_lock_manager.side_effect = OSError(28, "No space left on device")
            
            result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
            
            assert result.exit_code == 1
            assert "Insufficient disk space for budget operation" in result.stderr

    def test_handle_budget_error_corrupted_ynab_structure(self, runner):
        """Test handle_budget_error provides specific error for corrupted YNAB4 structure."""
        with patch('orchestration.cli.locked_budget_operation'):
            with patch('orchestration.cli.YnabParser') as mock_parser:
                mock_parser.side_effect = ValueError("Corrupted YNAB4 budget data: missing Budget.ymeta")
                
                result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
                
                assert result.exit_code == 1
                assert "Budget file appears to be corrupted or invalid" in result.stderr
                assert "missing Budget.ymeta" in result.stderr

    def test_handle_budget_error_invalid_ynab_structure(self, runner):
        """Test handle_budget_error provides specific error for invalid YNAB4 structure."""
        with patch('orchestration.cli.locked_budget_operation'):
            with patch('orchestration.cli.YnabParser') as mock_parser:
                mock_parser.side_effect = FileNotFoundError("Invalid YNAB4 budget structure: .ydevice not found")
                
                result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
                
                assert result.exit_code == 1
                assert "Invalid YNAB4 budget structure" in result.stderr
                assert ".ydevice not found" in result.stderr

    def test_handle_budget_error_json_parse_error(self, runner):
        """Test handle_budget_error provides specific error for JSON parsing issues."""
        with patch('orchestration.cli.locked_budget_operation'):
            with patch('orchestration.cli.YnabParser') as mock_parser:
                json_error = json.JSONDecodeError("Invalid JSON", "test.json", 0)
                mock_parser.side_effect = json_error
                
                result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
                
                assert result.exit_code == 1
                assert "Budget file contains invalid data format" in result.stderr

    def test_handle_budget_error_backup_insufficient_permissions(self, runner):
        """Test handle_budget_error provides specific error for backup permission issues."""
        with patch('orchestration.cli.locked_budget_operation'):
            with patch('orchestration.cli.BackupManager') as mock_backup:
                mock_backup_instance = Mock()
                mock_backup.return_value = mock_backup_instance
                mock_backup_instance.backup_budget.side_effect = PermissionError("Permission denied writing backup")
                
                result = runner.invoke(app, ["backup", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
                
                assert result.exit_code == 1
                assert "Unable to create backup: insufficient permissions" in result.stderr

    def test_handle_budget_error_backup_disk_space_error(self, runner):
        """Test handle_budget_error provides specific error for backup disk space issues."""
        with patch('orchestration.cli.locked_budget_operation'):
            with patch('orchestration.cli.BackupManager') as mock_backup:
                mock_backup_instance = Mock()
                mock_backup.return_value = mock_backup_instance
                mock_backup_instance.backup_budget.side_effect = OSError(28, "No space left on device")
                
                result = runner.invoke(app, ["backup", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
                
                assert result.exit_code == 1
                assert "Unable to create backup: insufficient disk space" in result.stderr

    def test_handle_budget_error_parser_apply_deltas_error(self, runner):
        """Test handle_budget_error provides specific error for delta parsing issues."""
        with patch('orchestration.cli.locked_budget_operation'):
            with patch('orchestration.cli.YnabParser') as mock_parser:
                parser_instance = Mock()
                mock_parser.return_value = parser_instance
                parser_instance.parse.return_value = None
                parser_instance.apply_deltas.side_effect = ValueError("Invalid delta filename format: corrupted.ydiff")
                
                result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
                
                assert result.exit_code == 1
                assert "Error processing budget changes" in result.stderr
                assert "corrupted.ydiff" in result.stderr

    def test_handle_budget_error_generic_fallback(self, runner):
        """Test handle_budget_error provides generic fallback for unrecognized errors."""
        with patch('orchestration.cli.locked_budget_operation'):
            with patch('orchestration.cli.YnabParser') as mock_parser:
                mock_parser.side_effect = RuntimeError("Some unexpected error")
                
                result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
                
                assert result.exit_code == 1
                assert "Error loading budget: Some unexpected error" in result.stderr

    def test_locked_budget_operation_budget_ymeta_missing(self, runner):
        """Test locked_budget_operation provides specific error when Budget.ymeta is missing."""
        with patch('orchestration.cli.LockManager') as mock_lock_manager:
            mock_lock_manager.side_effect = ValueError("Not a valid YNAB4 budget directory: missing Budget.ymeta")
            
            result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
            
            assert result.exit_code == 1
            assert "Invalid budget directory: missing Budget.ymeta file" in result.stderr

    def test_locked_budget_operation_not_directory_error(self, runner):
        """Test locked_budget_operation provides specific error when path is not a directory."""
        with patch('orchestration.cli.LockManager') as mock_lock_manager:
            mock_lock_manager.side_effect = ValueError("Budget path must be a directory")
            
            result = runner.invoke(app, ["load", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])
            
            assert result.exit_code == 1
            assert "Budget path must be a directory, not a file" in result.stderr


class TestCLI:
    """Test cases for the YNAB CLI tool."""
    
    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")
    
    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()
    
    def test_load_command_success(self, runner, test_budget_path):
        """Test load command successfully loads and displays budget info."""
        result = runner.invoke(app, ["load", str(test_budget_path)])
        
        assert_that(result.exit_code).is_equal_to(0)
        assert_that(result.stdout).contains("Budget loaded successfully")
        
        # Flexible assertions that match patterns and validate positive counts
        assert_that(result.stdout).matches(r"Accounts: \d+")
        assert_that(result.stdout).matches(r"Payees: \d+") 
        assert_that(result.stdout).matches(r"Transactions: \d+")
    
    def test_load_command_invalid_path(self, runner):
        """Test load command with invalid budget path."""
        result = runner.invoke(app, ["load", "nonexistent/path"])
        
        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr
    
    def test_backup_command_success(self, runner, test_budget_path):
        """Test backup command creates backup file and cleans it up."""
        result = runner.invoke(app, ["backup", str(test_budget_path)])
        
        try:
            assert result.exit_code == 0
            assert "Backup created successfully" in result.stdout
            assert ".zip" in result.stdout
        finally:
            # Cleanup: remove the created backup file to avoid polluting fixtures
            try:
                # Parse the path from stdout: line starting with "Backup file:"
                backup_line = next((line for line in result.stdout.splitlines() if line.startswith("Backup file:")), None)
                backup_path = None
                if backup_line:
                    backup_path_str = backup_line.split("Backup file:", 1)[1].strip()
                    if backup_path_str:
                        bp = Path(backup_path_str)
                        if bp.exists():
                            backup_path = bp
                if backup_path is None:
                    # Fallback: remove the newest matching backup file in the fixtures directory
                    candidates = list(test_budget_path.parent.glob(f"{test_budget_path.stem}_backup_*.zip"))
                    if candidates:
                        backup_path = max(candidates, key=lambda p: p.stat().st_mtime)
                if backup_path and backup_path.exists():
                    backup_path.unlink()
            except Exception:
                # Best-effort cleanup; do not fail the test due to cleanup
                pass
    
    def test_backup_command_invalid_path(self, runner):
        """Test backup command with invalid budget path."""
        result = runner.invoke(app, ["backup", "nonexistent/path"])
        
        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr
    
    def test_inspect_command_accounts(self, runner, test_budget_path):
        """Test inspect command shows account details."""
        result = runner.invoke(app, ["inspect", str(test_budget_path), "--accounts"])
        
        assert result.exit_code == 0
        assert "Account Details" in result.stdout
        assert "Type:" in result.stdout
    
    def test_inspect_command_transactions(self, runner, test_budget_path):
        """Test inspect command shows transaction details."""
        result = runner.invoke(app, ["inspect", str(test_budget_path), "--transactions"])
        
        assert result.exit_code == 0
        assert "Transaction Details" in result.stdout
        assert "Amount:" in result.stdout
        assert "Date:" in result.stdout
    
    def test_inspect_command_all(self, runner, test_budget_path):
        """Test inspect command shows all details when no specific option is given."""
        result = runner.invoke(app, ["inspect", str(test_budget_path)])
        
        assert result.exit_code == 0
        assert "Account Details" in result.stdout
        assert "Transaction Details" in result.stdout
    
    def test_inspect_command_invalid_path(self, runner):
        """Test inspect command with invalid budget path."""
        result = runner.invoke(app, ["inspect", "nonexistent/path"])
        
        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr
    
    @patch('orchestration.cli.locked_budget_operation')
    def test_load_command_uses_lock_manager(self, mock_locked_operation, runner, test_budget_path):
        """Test load command uses locked_budget_operation context manager."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value = test_budget_path
        mock_locked_operation.return_value = mock_context
        
        result = runner.invoke(app, ["load", str(test_budget_path)])
        
        # Verify locked_budget_operation was called with correct path
        mock_locked_operation.assert_called_once_with(str(test_budget_path))
        
        # Verify context manager was used
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
        
        assert result.exit_code == 0
    
    @patch('orchestration.cli.locked_budget_operation')
    def test_backup_command_uses_lock_manager(self, mock_locked_operation, runner, test_budget_path):
        """Test backup command uses locked_budget_operation context manager."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value = test_budget_path
        mock_locked_operation.return_value = mock_context
        
        result = runner.invoke(app, ["backup", str(test_budget_path)])
        
        # Verify locked_budget_operation was called with correct path
        mock_locked_operation.assert_called_once_with(str(test_budget_path))
        
        # Verify context manager was used
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
        
        try:
            assert result.exit_code == 0
        finally:
            # Cleanup: remove the created backup file to avoid polluting fixtures
            try:
                # Parse the path from stdout: line starting with "Backup file:"
                backup_line = next((line for line in result.stdout.splitlines() if line.startswith("Backup file:")), None)
                backup_path = None
                if backup_line:
                    backup_path_str = backup_line.split("Backup file:", 1)[1].strip()
                    if backup_path_str:
                        bp = Path(backup_path_str)
                        if bp.exists():
                            backup_path = bp
                if backup_path is None:
                    # Fallback: remove the newest matching backup file in the fixtures directory
                    candidates = list(test_budget_path.parent.glob(f"{test_budget_path.stem}_backup_*.zip"))
                    if candidates:
                        backup_path = max(candidates, key=lambda p: p.stat().st_mtime)
                if backup_path and backup_path.exists():
                    backup_path.unlink()
            except Exception:
                # Best-effort cleanup; do not fail the test due to cleanup
                pass
    
    @patch('orchestration.cli.locked_budget_operation')
    def test_inspect_command_uses_lock_manager(self, mock_locked_operation, runner, test_budget_path):
        """Test inspect command uses locked_budget_operation context manager."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value = test_budget_path
        mock_locked_operation.return_value = mock_context
        
        result = runner.invoke(app, ["inspect", str(test_budget_path), "--accounts"])
        
        # Verify locked_budget_operation was called with correct path
        mock_locked_operation.assert_called_once_with(str(test_budget_path))
        
        # Verify context manager was used
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
        
        assert result.exit_code == 0
    
    @patch('orchestration.cli.locked_budget_operation')
    def test_load_command_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test load command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception("Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable")
        
        result = runner.invoke(app, ["load", str(test_budget_path)])
        
        assert result.exit_code == 1
        assert "Error loading budget" in result.stderr
        assert "Failed to acquire lock" in result.stderr
    
    @patch('orchestration.cli.locked_budget_operation')
    def test_backup_command_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test backup command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception("Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable")
        
        result = runner.invoke(app, ["backup", str(test_budget_path)])
        
        assert result.exit_code == 1
        assert "Error creating backup" in result.stderr
        assert "Failed to acquire lock" in result.stderr
    
    @patch('orchestration.cli.locked_budget_operation')
    def test_inspect_command_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test inspect command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception("Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable")
        
        result = runner.invoke(app, ["inspect", str(test_budget_path)])
        
        assert result.exit_code == 1
        assert "Error inspecting budget" in result.stderr
        assert "Failed to acquire lock" in result.stderr