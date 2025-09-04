"""YNAB CLI Tool - Wrapping YnabParser, BackupManager, and LockManager functionality."""

import json
from pathlib import Path
from typing import Optional, Any, Callable, TypeVar, Union
from contextlib import contextmanager

import typer
from typing_extensions import Annotated

from ynab_io.parser import YnabParser
from ynab_io.safety import BackupManager, LockManager

# Constants
DEFAULT_ITEM_LIMIT = 3

# Type variable for generic functions
T = TypeVar('T')

# Create the Typer app
app = typer.Typer(help="YNAB4 Budget CLI Tool")


@contextmanager
def locked_budget_operation(budget_path: str):
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
    except Exception as e:
        # LockManager exceptions are re-raised as general exceptions
        # so they'll be handled by the calling function's error handler
        raise

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

def handle_budget_error(operation: str, error: Exception) -> None:
    """
    Handle budget operation errors with consistent messaging.
    
    Args:
        operation: Description of the operation that failed
        error: The exception that was raised
    """
    if isinstance(error, FileNotFoundError):
        typer.echo("Error: Budget path does not exist", err=True)
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
    budget_path: Annotated[str, typer.Argument(help="Path to the .ynab4 budget directory")]
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
    budget_path: Annotated[str, typer.Argument(help="Path to the .ynab4 budget directory")]
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