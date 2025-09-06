"""Test cases for the YNAB CLI tool - reorganized per subcommand."""

import errno
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from assertpy import assert_that
from filelock import Timeout
from typer.testing import CliRunner

from orchestration.cli import app


# Shared fixtures and utilities
@pytest.fixture
def test_budget_path():
    """Path to the test budget fixture."""
    return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


def cleanup_backup_file(result, test_budget_path):
    """Helper function to cleanup backup files after tests."""
    try:
        # Parse the path from stdout: line starting with "Backup file:"
        backup_line = next(
            (line for line in result.stdout.splitlines() if line.startswith("Backup file:")),
            None,
        )
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


class TestEnhancedErrorHandling:
    """Test cases for enhanced error handling in the CLI tool."""

    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()

    def test_locked_budget_operation_filelock_timeout_error(self, runner):
        """Test locked_budget_operation handles Timeout from filelock properly."""
        with patch("orchestration.cli.LockManager") as mock_lock_manager:
            mock_lock_manager.side_effect = Timeout("tests/fixtures/My Test Budget~E0C1460F.ynab4")

            result = runner.invoke(
                app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
            )

            assert result.exit_code == 1
            assert "Unable to acquire budget lock: Another application may be using this budget" in result.stderr

    def test_locked_budget_operation_permission_denied_error(self, runner):
        """Test locked_budget_operation handles PermissionError properly."""
        with patch("orchestration.cli.LockManager") as mock_lock_manager:
            mock_lock_manager.side_effect = PermissionError("Permission denied")

            result = runner.invoke(
                app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
            )

            assert result.exit_code == 1
            assert "Permission denied accessing budget files" in result.stderr

    def test_locked_budget_operation_disk_space_error(self, runner):
        """Test locked_budget_operation handles disk space errors properly."""
        with patch("orchestration.cli.LockManager") as mock_lock_manager:
            disk_error = OSError("No space left on device")
            disk_error.errno = errno.ENOSPC
            mock_lock_manager.side_effect = disk_error

            result = runner.invoke(
                app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
            )

            assert result.exit_code == 1
            assert "Insufficient disk space for budget operation" in result.stderr

    def test_handle_budget_error_corrupted_ynab_structure(self, runner):
        """Test handle_budget_error provides specific message for corrupted YNAB structure."""
        with patch("orchestration.cli.locked_budget_operation"):
            with patch("orchestration.cli.YnabParser") as mock_parser:
                mock_parser.side_effect = ValueError("Corrupted YNAB4 budget data: Invalid transaction format")

                result = runner.invoke(
                    app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
                )

                assert result.exit_code == 1
                assert "Budget file appears to be corrupted or invalid: Invalid transaction format" in result.stderr

    def test_handle_budget_error_invalid_ynab_structure(self, runner):
        """Test handle_budget_error provides specific message for invalid YNAB structure."""
        with patch("orchestration.cli.locked_budget_operation"):
            with patch("orchestration.cli.YnabParser") as mock_parser:
                mock_parser.side_effect = FileNotFoundError(
                    "Invalid YNAB4 budget structure: Missing required Budget.yfull file"
                )

                result = runner.invoke(
                    app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
                )

                assert result.exit_code == 1
                assert "Invalid YNAB4 budget structure: Missing required Budget.yfull file" in result.stderr

    def test_handle_budget_error_json_parse_error(self, runner):
        """Test handle_budget_error provides specific message for JSON parsing errors."""
        with patch("orchestration.cli.locked_budget_operation"):
            with patch("orchestration.cli.YnabParser") as mock_parser:
                mock_parser.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)

                result = runner.invoke(
                    app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
                )

                assert result.exit_code == 1
                assert "Budget file contains invalid data format" in result.stderr

    def test_handle_budget_error_backup_insufficient_permissions(self, runner):
        """Test handle_budget_error provides specific message for backup permission errors."""
        with patch("orchestration.cli.locked_budget_operation"):
            with patch("orchestration.cli.BackupManager") as mock_backup:
                mock_backup.return_value.backup_budget.side_effect = PermissionError("Permission denied")

                result = runner.invoke(app, ["backup", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])

                assert result.exit_code == 1
                assert "Unable to create backup: insufficient permissions" in result.stderr

    def test_handle_budget_error_backup_disk_space_error(self, runner):
        """Test handle_budget_error provides specific message for backup disk space errors."""
        with patch("orchestration.cli.locked_budget_operation"):
            with patch("orchestration.cli.BackupManager") as mock_backup:
                disk_error = OSError("No space left on device")
                disk_error.errno = errno.ENOSPC
                mock_backup.return_value.backup_budget.side_effect = disk_error

                result = runner.invoke(app, ["backup", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"])

                assert result.exit_code == 1
                assert "Unable to create backup: insufficient disk space" in result.stderr

    def test_handle_budget_error_parser_apply_deltas_error(self, runner):
        """Test handle_budget_error provides specific message for delta parsing errors."""
        with patch("orchestration.cli.locked_budget_operation"):
            with patch("orchestration.cli.YnabParser") as mock_parser:
                mock_parser.return_value.apply_deltas.side_effect = ValueError(
                    "Invalid delta filename format: A-86_B-12.ydiff"
                )

                result = runner.invoke(
                    app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
                )

                assert result.exit_code == 1
                assert "Error processing budget changes: A-86_B-12.ydiff" in result.stderr

    def test_handle_budget_error_generic_fallback(self, runner):
        """Test handle_budget_error provides generic fallback for unrecognized errors."""
        with patch("orchestration.cli.locked_budget_operation"):
            with patch("orchestration.cli.YnabParser") as mock_parser:
                mock_parser.side_effect = RuntimeError("Some unexpected error")

                result = runner.invoke(
                    app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
                )

                assert result.exit_code == 1
                assert "Error loading budget: Some unexpected error" in result.stderr

    def test_locked_budget_operation_budget_ymeta_missing(self, runner):
        """Test locked_budget_operation provides specific error when Budget.ymeta is missing."""
        with patch("orchestration.cli.LockManager") as mock_lock_manager:
            mock_lock_manager.side_effect = ValueError("Not a valid YNAB4 budget directory: missing Budget.ymeta")

            result = runner.invoke(
                app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
            )

            assert result.exit_code == 1
            assert "Invalid budget directory: missing Budget.ymeta file" in result.stderr

    def test_locked_budget_operation_not_directory_error(self, runner):
        """Test locked_budget_operation provides specific error when path is not a directory."""
        with patch("orchestration.cli.LockManager") as mock_lock_manager:
            mock_lock_manager.side_effect = ValueError("Budget path must be a directory")

            result = runner.invoke(
                app, ["budget", "show", "--budget-path", "tests/fixtures/My Test Budget~E0C1460F.ynab4"]
            )

            assert result.exit_code == 1
            assert "Budget path must be a directory, not a file" in result.stderr


class TestBudgetCommands:
    """Test cases for budget subcommands."""

    def test_budget_show_success(self, runner, test_budget_path):
        """Test budget show command successfully loads and displays budget info."""
        result = runner.invoke(app, ["budget", "show", "--budget-path", str(test_budget_path)])

        assert_that(result.exit_code).is_equal_to(0)
        assert_that(result.stdout).contains("Budget loaded successfully")

        # Flexible assertions that match patterns and validate positive counts
        assert_that(result.stdout).matches(r"Accounts: \d+")
        assert_that(result.stdout).matches(r"Payees: \d+")
        assert_that(result.stdout).matches(r"Transactions: \d+")

    def test_budget_show_invalid_path(self, runner):
        """Test budget show command with invalid budget path."""
        result = runner.invoke(app, ["budget", "show", "--budget-path", "nonexistent/path"])

        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr

    @patch("orchestration.cli.locked_budget_operation")
    def test_budget_show_uses_lock_manager(self, mock_locked_operation, runner, test_budget_path):
        """Test budget show command uses locked_budget_operation context manager."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value = test_budget_path
        mock_locked_operation.return_value = mock_context

        result = runner.invoke(app, ["budget", "show", "--budget-path", str(test_budget_path)])

        # Verify locked_budget_operation was called with correct path
        mock_locked_operation.assert_called_once_with(str(test_budget_path))

        # Verify context manager was used
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()

        assert result.exit_code == 0

    @patch("orchestration.cli.locked_budget_operation")
    def test_budget_show_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test budget show command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception(
            "Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable"
        )

        result = runner.invoke(app, ["budget", "show", "--budget-path", str(test_budget_path)])

        assert result.exit_code == 1
        assert "Error loading budget" in result.stderr
        assert "Failed to acquire lock" in result.stderr


class TestAccountsCommands:
    """Test cases for accounts subcommands."""

    def test_accounts_list_success(self, runner, test_budget_path):
        """Test accounts list command shows account details."""
        result = runner.invoke(app, ["accounts", "list", "--budget-path", str(test_budget_path)])

        assert result.exit_code == 0
        assert "Account Details" in result.stdout
        assert "Type:" in result.stdout

    def test_accounts_list_invalid_path(self, runner):
        """Test accounts list command with invalid budget path."""
        result = runner.invoke(app, ["accounts", "list", "--budget-path", "nonexistent/path"])

        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr

    @patch("orchestration.cli.locked_budget_operation")
    def test_accounts_list_uses_lock_manager(self, mock_locked_operation, runner, test_budget_path):
        """Test accounts list command uses locked_budget_operation context manager."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value = test_budget_path
        mock_locked_operation.return_value = mock_context

        result = runner.invoke(app, ["accounts", "list", "--budget-path", str(test_budget_path)])

        # Verify locked_budget_operation was called with correct path
        mock_locked_operation.assert_called_once_with(str(test_budget_path))

        # Verify context manager was used
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()

        assert result.exit_code == 0

    @patch("orchestration.cli.locked_budget_operation")
    def test_accounts_list_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test accounts list command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception(
            "Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable"
        )

        result = runner.invoke(app, ["accounts", "list", "--budget-path", str(test_budget_path)])

        assert result.exit_code == 1
        assert "Error listing accounts" in result.stderr
        assert "Failed to acquire lock" in result.stderr


class TestBackupCommand:
    """Test cases for backup command."""

    def test_backup_success(self, runner, test_budget_path):
        """Test backup command creates backup file and cleans it up."""
        result = runner.invoke(app, ["backup", "--budget-path", str(test_budget_path)])

        try:
            assert result.exit_code == 0
            assert "Backup created successfully" in result.stdout
            assert ".zip" in result.stdout
        finally:
            cleanup_backup_file(result, test_budget_path)

    def test_backup_invalid_path(self, runner):
        """Test backup command with invalid budget path."""
        result = runner.invoke(app, ["backup", "--budget-path", "nonexistent/path"])

        assert result.exit_code == 1
        assert "Error: Budget path does not exist" in result.stderr

    @patch("orchestration.cli.locked_budget_operation")
    def test_backup_uses_lock_manager(self, mock_locked_operation, runner, test_budget_path):
        """Test backup command uses locked_budget_operation context manager."""
        mock_context = MagicMock()
        mock_context.__enter__.return_value = test_budget_path
        mock_locked_operation.return_value = mock_context

        result = runner.invoke(app, ["backup", "--budget-path", str(test_budget_path)])

        # Verify locked_budget_operation was called with correct path
        mock_locked_operation.assert_called_once_with(str(test_budget_path))

        # Verify context manager was used
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()

        try:
            assert result.exit_code == 0
        finally:
            cleanup_backup_file(result, test_budget_path)

    @patch("orchestration.cli.locked_budget_operation")
    def test_backup_lock_timeout_error(self, mock_locked_operation, runner, test_budget_path):
        """Test backup command handles lock timeout error."""
        mock_locked_operation.side_effect = Exception(
            "Failed to acquire lock for budget: [Errno 11] Resource temporarily unavailable"
        )

        result = runner.invoke(app, ["backup", "--budget-path", str(test_budget_path)])

        assert result.exit_code == 1
        assert "Error creating backup" in result.stderr
        assert "Failed to acquire lock" in result.stderr
