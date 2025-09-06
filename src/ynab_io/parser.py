import copy
import json
import logging
from pathlib import Path
from typing import Any

from .device_manager import DeviceManager
from .models import (
    Account,
    Budget,
    Category,
    MasterCategory,
    MonthlyBudget,
    MonthlyCategoryBudget,
    Payee,
    PayeeStringCondition,
    ScheduledTransaction,
    Transaction,
)


class YnabParser:
    def __init__(self, budget_path: Path):
        self.budget_path = budget_path
        try:
            self.device_manager = DeviceManager(budget_path)
            self.data_dir = self.device_manager.get_data_dir_path()
            device_guid = self.device_manager.get_active_device_guid()
            self.device_dir = self.device_manager.get_device_dir_path(device_guid)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Invalid YNAB4 budget structure: {e}")
        except ValueError as e:
            raise ValueError(f"Corrupted YNAB4 budget data: {e}")
        self.accounts: dict[str, Account] = {}
        self.payees: dict[str, Payee] = {}
        self.transactions: dict[str, Transaction] = {}
        self.master_categories: dict[str, MasterCategory] = {}
        self.categories: dict[str, Category] = {}
        self.monthly_budgets: dict[str, MonthlyBudget] = {}
        self.monthly_category_budgets: dict[str, MonthlyCategoryBudget] = {}
        self.scheduled_transactions: dict[str, ScheduledTransaction] = {}
        self.payee_string_conditions: dict[str, PayeeStringCondition] = {}

        # Version tracking state
        self.applied_deltas: list[Path] = []
        self._base_state: dict = {}

    def parse(self) -> Budget:
        """Parse the budget and apply all available deltas.

        Returns:
            Budget object at the latest version state
        """
        return self._parse_with_delta_strategy(lambda: self.apply_deltas())

    def parse_up_to_version(self, target_version: int) -> Budget:
        """Parse the budget and apply deltas only up to the specified version.

        This method provides version isolation by only parsing and applying deltas
        up to the target version, never processing newer deltas that might contain
        unsupported data types.

        Args:
            target_version: Version number to parse up to (0 = base state only)

        Returns:
            Budget object at the specified version state
        """

        def delta_strategy():
            if target_version > 0:
                self._apply_deltas_up_to_version(target_version)

        return self._parse_with_delta_strategy(delta_strategy)

    def _parse_with_delta_strategy(self, delta_strategy_func) -> Budget:
        """Parse base budget data and apply deltas using the provided strategy.

        Args:
            delta_strategy_func: Function that applies deltas according to specific strategy

        Returns:
            Budget object in the state after applying the delta strategy
        """
        device_guid = self.device_manager.get_active_device_guid()
        yfull_path = self.device_manager.get_budget_file_path(device_guid)
        with open(yfull_path, "r") as f:
            data = json.load(f)

        # Parse simple entities
        self._parse_entities(data.get("accounts", []), Account, self.accounts)
        self._parse_entities(data.get("payees", []), Payee, self.payees)
        self._parse_entities(data.get("transactions", []), Transaction, self.transactions)
        self._parse_entities(data.get("monthlyBudgets", []), MonthlyBudget, self.monthly_budgets)
        self._parse_entities(
            data.get("monthlyCategoryBudgets", []),
            MonthlyCategoryBudget,
            self.monthly_category_budgets,
        )
        self._parse_entities(
            data.get("scheduledTransactions", []),
            ScheduledTransaction,
            self.scheduled_transactions,
        )

        # Parse master categories with nested categories
        self._parse_master_categories(data.get("masterCategories", []))

        # Save base state before applying deltas
        self._save_base_state()

        # Apply deltas using the provided strategy
        delta_strategy_func()

        return self._create_budget_object()

    def _create_budget_object(self) -> Budget:
        """Create a Budget object from the current parser state.

        Returns:
            Budget object containing all parsed entities
        """
        return Budget(
            accounts=list(self.accounts.values()),
            payees=list(self.payees.values()),
            transactions=list(self.transactions.values()),
            master_categories=list(self.master_categories.values()),
            categories=list(self.categories.values()),
            monthly_budgets=list(self.monthly_budgets.values()),
            monthly_category_budgets=list(self.monthly_category_budgets.values()),
            scheduled_transactions=list(self.scheduled_transactions.values()),
            payee_string_conditions=list(self.payee_string_conditions.values()),
        )

    def _parse_entities(self, entity_data_list, model_class, collection):
        """Parse a list of entities into the specified collection."""
        for entity_data in entity_data_list:
            entity = model_class(**entity_data)
            collection[entity.entityId] = entity

    def _parse_master_categories(self, master_categories_data):
        """Parse master categories and their nested subcategories."""
        for master_category_data in master_categories_data:
            # Extract and process nested categories first
            if "subCategories" in master_category_data and master_category_data["subCategories"] is not None:
                for category_data in master_category_data["subCategories"]:
                    category = Category(**category_data)
                    self.categories[category.entityId] = category

            # Create master category without subCategories to avoid circular reference
            master_category_clean = {k: v for k, v in master_category_data.items() if k != "subCategories"}
            master_category = MasterCategory(**master_category_clean)
            self.master_categories[master_category.entityId] = master_category

    def _get_entity_mapping(self, entity_type):
        """Get the collection and model class for a given entity type."""
        entity_mappings = {
            # Basic entities
            "account": (self.accounts, Account),
            "payee": (self.payees, Payee),
            "payeeStringCondition": (self.payee_string_conditions, PayeeStringCondition),
            "transaction": (self.transactions, Transaction),
            # Category entities
            "masterCategory": (self.master_categories, MasterCategory),
            "category": (self.categories, Category),
            # Budget entities
            "monthlyBudget": (self.monthly_budgets, MonthlyBudget),
            "monthlyCategoryBudget": (
                self.monthly_category_budgets,
                MonthlyCategoryBudget,
            ),
            # Scheduled transactions
            "scheduledTransaction": (self.scheduled_transactions, ScheduledTransaction),
        }
        return entity_mappings.get(entity_type, (None, None))

    def apply_deltas(self):
        delta_files = self._discover_delta_files()
        for delta_file in delta_files:
            self._apply_delta(delta_file)
            self.applied_deltas.append(delta_file)

    def _discover_delta_files(self) -> list[Path]:
        ydiff_files = list(self.device_dir.glob("*.ydiff"))
        return sorted(ydiff_files, key=self._get_delta_sort_key)

    def _get_delta_sort_key(self, delta_path: Path) -> int:
        start_version, _ = self._parse_delta_versions(delta_path.name)
        return self._get_version_number_from_composite(start_version, f"delta file '{delta_path.name}'")

    def _get_version_number_from_composite(self, composite_version: str, context: str) -> int:
        """Extract the version number from a composite version string using DeviceManager methods.

        Args:
            composite_version: Version string (e.g., 'A-100' or 'A-100,B-200,C-50')
            context: Context string for error messages

        Returns:
            The version number from the latest version in the composite string
        """
        try:
            latest_version = self.device_manager.get_latest_version_from_composite(composite_version)
            _, version_num = self.device_manager.parse_version_string(latest_version)
            return version_num
        except ValueError as e:
            raise ValueError(f"Failed to parse version number from '{composite_version}' in {context}: {e}")

    def _parse_delta_versions(self, filename: str) -> tuple[str, str]:
        if not filename.endswith(".ydiff"):
            raise ValueError(f"Invalid delta filename format: {filename}")
        base_name = filename[:-6]
        try:
            start_version, end_version = base_name.split("_")
        except ValueError:
            raise ValueError(f"Invalid delta filename format: {filename}")
        return start_version, end_version

    def _apply_delta(self, delta_file: Path):
        with open(delta_file, "r") as f:
            delta_data = json.load(f)

        for item in delta_data.get("items", []):
            entity_id = item["entityId"]
            entity_type = item["entityType"]

            # Get collection and model for entity type
            collection, model = self._get_entity_mapping(entity_type)
            if collection is None:
                logging.warning(
                    f"Unknown entity type '{entity_type}' encountered in delta file '{delta_file.name}'. Entity ID: {entity_id}. Available keys: {list(item.keys())}"
                )
                continue

            if item["isTombstone"]:
                if entity_id in collection:
                    del collection[entity_id]
                continue

            if entity_id in collection:
                existing_entity = collection[entity_id]
                existing_version_num = self._get_version_number_from_composite(
                    existing_entity.entityVersion,
                    f"existing {entity_type} '{entity_id}' in delta file '{delta_file.name}'",
                )

                new_version_num = self._get_version_number_from_composite(
                    item["entityVersion"],
                    f"new {entity_type} '{entity_id}' in delta file '{delta_file.name}'",
                )

                if new_version_num > existing_version_num:
                    updated_data = existing_entity.model_dump()
                    updated_data.update(item)
                    collection[entity_id] = model(**updated_data)
            else:
                collection[entity_id] = model(**item)

    def _save_base_state(self):
        """Save the current state as the base state (before any deltas)."""
        self._base_state = self._capture_current_state()

    def restore_to_version(self, target_version: int):
        """Restore parser state to a specific version number.

        Args:
            target_version: Version number to restore to (0 = base state)

        Raises:
            ValueError: If target_version is invalid or not available
        """
        self._validate_target_version(target_version)

        # Restore to base state first
        self._restore_from_state(self._base_state)
        self.applied_deltas = []

        # If target version is 0, we're done (base state)
        if target_version == 0:
            return

        # Apply deltas up to target version
        self._apply_deltas_up_to_version(target_version)

    def _get_version_end_number(self, delta_path: Path) -> int:
        """Extract the end version number from a delta filename."""
        _, end_version = self._parse_delta_versions(delta_path.name)
        return self._get_version_number_from_composite(end_version, f"delta file '{delta_path.name}'")

    def get_available_versions(self) -> list[int]:
        """Get sorted list of available version numbers."""
        versions = [0]  # Base state version

        delta_files = self._discover_delta_files()
        for delta_file in delta_files:
            end_version = self._get_version_end_number(delta_file)
            versions.append(end_version)

        return sorted(versions)

    def _capture_current_state(self) -> dict[str, Any]:
        """Capture the current parser state as a deep copy.

        Returns:
            Dictionary containing deep copies of all entity collections
        """
        return {
            "accounts": copy.deepcopy(self.accounts),
            "payees": copy.deepcopy(self.payees),
            "transactions": copy.deepcopy(self.transactions),
            "master_categories": copy.deepcopy(self.master_categories),
            "categories": copy.deepcopy(self.categories),
            "monthly_budgets": copy.deepcopy(self.monthly_budgets),
            "monthly_category_budgets": copy.deepcopy(self.monthly_category_budgets),
            "scheduled_transactions": copy.deepcopy(self.scheduled_transactions),
            "payee_string_conditions": copy.deepcopy(self.payee_string_conditions),
        }

    def _restore_from_state(self, state: dict[str, Any]):
        """Restore parser collections from a saved state.

        Args:
            state: Dictionary containing entity collections to restore
        """
        self.accounts = copy.deepcopy(state["accounts"])
        self.payees = copy.deepcopy(state["payees"])
        self.transactions = copy.deepcopy(state["transactions"])
        self.master_categories = copy.deepcopy(state["master_categories"])
        self.categories = copy.deepcopy(state["categories"])
        self.monthly_budgets = copy.deepcopy(state["monthly_budgets"])
        self.monthly_category_budgets = copy.deepcopy(state["monthly_category_budgets"])
        self.scheduled_transactions = copy.deepcopy(state["scheduled_transactions"])
        self.payee_string_conditions = copy.deepcopy(state["payee_string_conditions"])

    def _validate_target_version(self, target_version: int):
        """Validate that target version is valid and available.

        Args:
            target_version: Version number to validate

        Raises:
            ValueError: If target_version is invalid or not available
        """
        if target_version < 0:
            raise ValueError(f"Version {target_version} is invalid: version must be non-negative")

        available_versions = self.get_available_versions()
        if target_version not in available_versions:
            raise ValueError(f"Version {target_version} not found in available versions: {available_versions}")

    def _apply_deltas_up_to_version(self, target_version: int):
        """Apply delta files up to the specified target version.

        Args:
            target_version: Version number to apply deltas up to
        """
        delta_files = self._discover_delta_files()
        for delta_file in delta_files:
            end_version = self._get_version_end_number(delta_file)
            if end_version <= target_version:
                self._apply_delta(delta_file)
                self.applied_deltas.append(delta_file)
            else:
                break
