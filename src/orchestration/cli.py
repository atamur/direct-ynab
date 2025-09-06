"""YNAB CLI Tool - Wrapping YnabParser, BackupManager, and LockManager functionality."""

import errno
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, TypeVar

import typer
from filelock import Timeout
from typing_extensions import Annotated
from ynab_io.parser import YnabParser
from ynab_io.safety import BackupManager, LockManager

# Constants
DEFAULT_ITEM_LIMIT = 3


# Error message templates
ERROR_LOCK_TIMEOUT = "Unable to acquire budget lock: Another application may be using this budget"
ERROR_PERMISSION_DENIED = "Permission denied accessing budget files"
ERROR_INSUFFICIENT_DISK_SPACE = "Insufficient disk space for budget operation"
ERROR_INVALID_BUDGET_DIR = "Invalid budget directory: missing Budget.ymeta file"
ERROR_NOT_DIRECTORY = "Budget path must be a directory, not a file"
ERROR_BUDGET_CORRUPTED = "Budget file appears to be corrupted or invalid"
ERROR_JSON_INVALID = "Budget file contains invalid data format"
ERROR_DELTA_PROCESSING = "Error processing budget changes"
ERROR_BACKUP_PERMISSION = "Unable to create backup: insufficient permissions"
ERROR_BACKUP_DISK_SPACE = "Unable to create backup: insufficient disk space"


# Type variable for generic functions
T = TypeVar("T")


# Create the Typer app
app = typer.Typer(help="YNAB4 Budget CLI Tool")


@contextmanager
def locked_budget_operation(budget_path: str) -> Generator[Path, None, None]:
    """
    Context manager that validates budget path and acquires lock for safe operations.

    Args:
        budget_path: String path to budget directory

    Yields:
        Path: Validated Path object

    Raises:
        typer.Exit: If path doesn't exist or lock cannot be acquired
    """
    path = Path(budget_path)
    if not path.exists():
        typer.echo("Error: Budget path does not exist", err=True)
        raise typer.Exit(1)

    try:
        with LockManager(path):
            yield path
    except Timeout:
        typer.echo(ERROR_LOCK_TIMEOUT, err=True)
        raise typer.Exit(1)
    except PermissionError:
        typer.echo(ERROR_PERMISSION_DENIED, err=True)
        raise typer.Exit(1)
    except OSError as e:
        if e.errno == errno.ENOSPC:
            typer.echo(ERROR_INSUFFICIENT_DISK_SPACE, err=True)
        else:
            typer.echo(f"System error accessing budget: {e}", err=True)
        raise typer.Exit(1)
    except ValueError as e:
        _handle_value_error_in_lock_operation(e)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error accessing budget: {e}", err=True)
        raise typer.Exit(1)


def validate_budget_path(budget_path: str) -> Path:
    """
    Validate that the budget path exists and return Path object.

    Args:
        budget_path: String path to budget directory

    Returns:
        Path object if valid

    Raises:
        typer.Exit: If path doesn't exist (exits with code 1)
    """
    path = Path(budget_path)
    if not path.exists():
        typer.echo("Error: Budget path does not exist", err=True)
        raise typer.Exit(1)
    return path


def _handle_value_error_in_lock_operation(error: ValueError) -> None:
    """
    Handle ValueError exceptions in locked_budget_operation context manager.

    Args:
        error: The ValueError that was raised
    """
    error_msg = str(error)
    if "missing Budget.ymeta" in error_msg:
        typer.echo(ERROR_INVALID_BUDGET_DIR, err=True)
    elif "Budget path must be a directory" in error_msg:
        typer.echo(ERROR_NOT_DIRECTORY, err=True)
    else:
        typer.echo(f"Invalid budget configuration: {error}", err=True)


def _extract_error_detail(error_msg: str, delimiter: str = ": ") -> str:
    """
    Extract the detailed error message after the last delimiter.

    Args:
        error_msg: Full error message
        delimiter: Delimiter to split on (default ": ")

    Returns:
        Detailed error message or full original message if delimiter not found
    """
    if delimiter in error_msg:
        return error_msg.split(delimiter)[-1]
    return error_msg


def handle_budget_error(operation: str, error: Exception) -> None:
    """
    Handle budget operation errors with consistent messaging.

    Args:
        operation: Description of the operation that failed
        error: The exception that was raised
    """
    error_msg = str(error)

    # Handle JSON parsing errors (must be before ValueError since JSONDecodeError inherits from ValueError)
    if isinstance(error, json.JSONDecodeError):
        typer.echo(ERROR_JSON_INVALID, err=True)

    # Handle FileNotFoundError
    elif isinstance(error, FileNotFoundError):
        if "Invalid YNAB4 budget structure" in error_msg:
            detail = _extract_error_detail(error_msg)
            typer.echo(f"Invalid YNAB4 budget structure: {detail}", err=True)
        else:
            typer.echo("Error: Budget path does not exist", err=True)

    # Handle ValueError (corrupted data, invalid structure, delta parsing errors)
    elif isinstance(error, ValueError):
        if "Corrupted YNAB4 budget data" in error_msg:
            detail = _extract_error_detail(error_msg)
            typer.echo(f"{ERROR_BUDGET_CORRUPTED}: {detail}", err=True)
        elif "Invalid delta filename format" in error_msg:
            delta_file = _extract_error_detail(error_msg)
            typer.echo(f"{ERROR_DELTA_PROCESSING}: {delta_file}", err=True)
        else:
            typer.echo(f"Error {operation}: {error}", err=True)

    # Handle permission errors for backup operations
    elif isinstance(error, PermissionError):
        if "backup" in operation:
            typer.echo(ERROR_BACKUP_PERMISSION, err=True)
        else:
            typer.echo(f"Error {operation}: {error}", err=True)

    # Handle disk space errors
    elif isinstance(error, OSError) and getattr(error, "errno", None) == errno.ENOSPC:
        if "backup" in operation:
            typer.echo(ERROR_BACKUP_DISK_SPACE, err=True)
        else:
            typer.echo(f"Error {operation}: {error}", err=True)

    # Generic fallback
    else:
        typer.echo(f"Error {operation}: {error}", err=True)

    raise typer.Exit(1)


def format_currency(amount: float) -> str:
    """
    Format currency amount.

    Args:
        amount: Amount

    Returns:
        Formatted currency string
    """
    return f"${amount:.2f}"


def display_accounts(parser: YnabParser, limit: int = DEFAULT_ITEM_LIMIT) -> None:
    """
    Display account details with name, balance, and type.

    Args:
        parser: YnabParser object containing accounts
        limit: Maximum number of accounts to display
    """
    typer.echo("Account Details:")
    for account in list(parser.accounts.values())[:limit]:
        typer.echo(f"  - {account.accountName}")
        typer.echo(f"    Type: {account.accountType}")


def display_transactions(parser: YnabParser, limit: int = DEFAULT_ITEM_LIMIT) -> None:
    """
    Display transaction details with memo, amount, and date.

    Args:
        parser: YnabParser object containing transactions
        limit: Maximum number of transactions to display
    """
    typer.echo("Transaction Details:")
    for transaction in list(parser.transactions.values())[:limit]:
        payee = parser.payees.get(transaction.payeeId)
        payee_name = payee.name if payee else "Unknown Payee"
        typer.echo(f"  - {payee_name}")
        typer.echo(f"    Amount: {format_currency(transaction.amount)}")
        typer.echo(f"    Date: {transaction.date}")


@app.command()
def load(
    budget_path: Annotated[str, typer.Argument(help="Path to the .ynab4 budget directory")],
) -> None:
    """Load and display basic budget information."""
    try:
        with locked_budget_operation(budget_path) as path:
            # Load the budget
            parser = YnabParser(path)
            parser.parse()
            parser.apply_deltas()

            # Display basic info
            typer.echo("Budget loaded successfully")
            typer.echo(f"Accounts: {len(parser.accounts)}")
            typer.echo(f"Payees: {len(parser.payees)}")
            typer.echo(f"Transactions: {len(parser.transactions)}")

    except Exception as e:
        handle_budget_error("loading budget", e)


@app.command()
def backup(
    budget_path: Annotated[str, typer.Argument(help="Path to the .ynab4 budget directory")],
) -> None:
    """Create a backup of the budget."""
    try:
        with locked_budget_operation(budget_path) as path:
            # Create backup
            backup_manager = BackupManager()
            backup_file = backup_manager.backup_budget(path)

            typer.echo("Backup created successfully")
            typer.echo(f"Backup file: {backup_file}")

    except Exception as e:
        handle_budget_error("creating backup", e)


@app.command()
def inspect(
    budget_path: Annotated[str, typer.Argument(help="Path to the .ynab4 budget directory")],
    accounts: Annotated[bool, typer.Option("--accounts", help="Show account details")] = False,
    transactions: Annotated[bool, typer.Option("--transactions", help="Show transaction details")] = False,
) -> None:
    """Inspect budget details (accounts, transactions)."""
    try:
        with locked_budget_operation(budget_path) as path:
            # Load the budget
            parser = YnabParser(path)
            parser.parse()
            parser.apply_deltas()

            # If no specific option, show all
            show_all = not (accounts or transactions)

            if show_all or accounts:
                display_accounts(parser)

            if show_all or transactions:
                display_transactions(parser)

    except Exception as e:
        handle_budget_error("inspecting budget", e)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
