"""YNAB CLI Tool - Wrapping BudgetReader, BackupManager, and LockManager functionality."""

import json
from pathlib import Path
from typing import Optional, Any, Callable, TypeVar, Union
from contextlib import contextmanager

import typer
from typing_extensions import Annotated

from ynab_io.reader import BudgetReader
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


def format_currency(amount_cents: int) -> str:
    """
    Format currency amount from cents to dollars.
    
    Args:
        amount_cents: Amount in cents
        
    Returns:
        Formatted currency string
    """
    return f"${amount_cents/100:.2f}"


def display_accounts(budget: Any, limit: int = DEFAULT_ITEM_LIMIT) -> None:
    """
    Display account details with name, balance, and type.
    
    Args:
        budget: Budget object containing accounts
        limit: Maximum number of accounts to display
    """
    typer.echo("Account Details:")
    for account in budget.accounts[:limit]:
        typer.echo(f"  - {account.name}")
        typer.echo(f"    Balance: {format_currency(account.balance)}")
        account_type = getattr(account, 'account_type', getattr(account, 'type', 'Unknown'))
        typer.echo(f"    Type: {account_type}")


def display_categories(budget: Any, limit: int = DEFAULT_ITEM_LIMIT) -> None:
    """
    Display category details with name and budgeted amounts.
    
    Args:
        budget: Budget object containing categories
        limit: Maximum number of categories to display
    """
    typer.echo("Category Details:")
    for category in budget.categories[:limit]:
        typer.echo(f"  - {category.name}")
        budgeted = getattr(category, 'budgeted', 0)
        typer.echo(f"    Budgeted: {format_currency(budgeted)}")


def display_transactions(budget: Any, limit: int = DEFAULT_ITEM_LIMIT) -> None:
    """
    Display transaction details with memo, amount, and date.
    
    Args:
        budget: Budget object containing transactions
        limit: Maximum number of transactions to display
    """
    typer.echo("Transaction Details:")
    for transaction in budget.transactions[:limit]:
        typer.echo(f"  - {transaction.memo or 'No memo'}")
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
            reader = BudgetReader(path)
            budget = reader.load_snapshot()
            
            # Display basic info
            typer.echo("Budget loaded successfully")
            typer.echo(f"Budget: {reader._extract_budget_name()}")
            
            # Show basic stats
            typer.echo(f"Accounts: {len(budget.accounts)}")
            typer.echo(f"Categories: {len(budget.categories)}")
        
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
    categories: Annotated[bool, typer.Option("--categories", help="Show category details")] = False,
    transactions: Annotated[bool, typer.Option("--transactions", help="Show transaction details")] = False,
) -> None:
    """Inspect budget details (accounts, categories, transactions)."""
    try:
        with locked_budget_operation(budget_path) as path:
            # Load the budget
            reader = BudgetReader(path)
            budget = reader.load_snapshot()
            
            # If no specific option, show all
            show_all = not (accounts or categories or transactions)
            
            if show_all or accounts:
                display_accounts(budget)
            
            if show_all or categories:
                display_categories(budget)
            
            if show_all or transactions:
                display_transactions(budget)
                
    except Exception as e:
        handle_budget_error("inspecting budget", e)


@app.command()
def deltas(
    budget_path: Annotated[str, typer.Argument(help="Path to the .ynab4 budget directory")],
    show: Annotated[Optional[str], typer.Option("--show", help="Show content of specific delta file")] = None,
) -> None:
    """List and show delta files."""
    try:
        with locked_budget_operation(budget_path) as path:
            # Load the budget and discover deltas
            reader = BudgetReader(path)
            reader.load_snapshot()
            delta_files = reader.discover_delta_files()
            
            if show:
                # Find and show specific delta file
                delta_file = next((df for df in delta_files if df.name == show), None)
                
                if not delta_file:
                    typer.echo("Error: Delta file not found", err=True)
                    raise typer.Exit(1)
                
                typer.echo("Delta File Content:")
                delta_data = reader._load_delta_file(delta_file)
                typer.echo(json.dumps(delta_data, indent=2))
            else:
                # List all delta files
                typer.echo("Delta Files Found:")
                for delta_file in delta_files:
                    typer.echo(f"  - {delta_file.name}")
                
    except Exception as e:
        handle_budget_error("processing deltas", e)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()