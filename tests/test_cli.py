"""Tests for the YNAB CLI tool."""

import json
import zipfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from typer.testing import CliRunner
import pytest
from filelock import Timeout

from ynab_io.orchestration.cli import app


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
        
        assert result.exit_code == 0
        assert "Budget loaded successfully" in result.stdout
        assert "My Test Budget" in result.stdout
        assert "Accounts:" in result.stdout
        assert "Categories:" in result.stdout
    
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
        assert "Balance:" in result.stdout
        assert "Type:" in result.stdout
    
    def test_inspect_command_categories(self, runner, test_budget_path):
        """Test inspect command shows category details."""
        result = runner.invoke(app, ["inspect", str(test_budget_path), "--categories"])
        
        assert result.exit_code == 0
        assert "Category Details" in result.stdout
        assert "Budgeted:" in result.stdout
    
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
        assert "Category Details" in result.stdout
        assert "Transaction Details" in result.stdout
    
    def test_inspect_command_invalid_path(self, runner):
        """Test inspect command with invalid budget path."""
        result = runner.invoke(app, ["inspect", "nonexistent/path"])
        
        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr
    
    def test_deltas_command_list(self, runner, test_budget_path):
        """Test deltas command lists available delta files."""
        result = runner.invoke(app, ["deltas", str(test_budget_path)])
        
        assert result.exit_code == 0
        assert "Delta Files Found:" in result.stdout
        assert "A-63_A-67.ydiff" in result.stdout
        assert "A-67_A-69.ydiff" in result.stdout
        assert "A-69_A-71.ydiff" in result.stdout
        assert "A-71_A-72.ydiff" in result.stdout
    
    def test_deltas_command_show_content(self, runner, test_budget_path):
        """Test deltas command shows content of a specific delta file."""
        result = runner.invoke(app, ["deltas", str(test_budget_path), "--show", "A-63_A-67.ydiff"])
        
        assert result.exit_code == 0
        assert "Delta File Content" in result.stdout
        assert "items" in result.stdout
    
    def test_deltas_command_invalid_path(self, runner):
        """Test deltas command with invalid budget path."""
        result = runner.invoke(app, ["deltas", "nonexistent/path"])
        
        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr
    
    def test_deltas_command_invalid_delta_file(self, runner, test_budget_path):
        """Test deltas command with invalid delta file name."""
        result = runner.invoke(app, ["deltas", str(test_budget_path), "--show", "nonexistent.ydiff"])
        
        assert result.exit_code == 1
        assert "Error: Delta file not found" in result.stderr
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
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
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
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
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
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
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
    def test_deltas_command_uses_lock_manager(self, mock_locked_operation, runner, test_budget_path):
        """Test deltas command uses locked_budget_operation context manager."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value = test_budget_path
        mock_locked_operation.return_value = mock_context
        
        result = runner.invoke(app, ["deltas", str(test_budget_path)])
        
        # Verify locked_budget_operation was called with correct path
        mock_locked_operation.assert_called_once_with(str(test_budget_path))
        
        # Verify context manager was used
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
        
        assert result.exit_code == 0
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
    def test_load_command_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test load command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception("Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable")
        
        result = runner.invoke(app, ["load", str(test_budget_path)])
        
        assert result.exit_code == 1
        assert "Error loading budget" in result.stderr
        assert "Failed to acquire lock" in result.stderr
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
    def test_backup_command_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test backup command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception("Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable")
        
        result = runner.invoke(app, ["backup", str(test_budget_path)])
        
        assert result.exit_code == 1
        assert "Error creating backup" in result.stderr
        assert "Failed to acquire lock" in result.stderr
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
    def test_inspect_command_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test inspect command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception("Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable")
        
        result = runner.invoke(app, ["inspect", str(test_budget_path)])
        
        assert result.exit_code == 1
        assert "Error inspecting budget" in result.stderr
        assert "Failed to acquire lock" in result.stderr
    
    @patch('ynab_io.orchestration.cli.locked_budget_operation')
    def test_deltas_command_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test deltas command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception("Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable")
        
        result = runner.invoke(app, ["deltas", str(test_budget_path)])
        
        assert result.exit_code == 1
        assert "Error processing deltas" in result.stderr
        assert "Failed to acquire lock" in result.stderr