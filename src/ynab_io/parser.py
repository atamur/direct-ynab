import json
import logging
from pathlib import Path
from typing import List, Dict

from .models import (
    Account,
    Payee,
    Transaction,
    MasterCategory,
    Category,
    MonthlyBudget,
    MonthlyCategoryBudget,
    ScheduledTransaction,
    Budget,
)
from .device_manager import DeviceManager


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
        self.accounts: Dict[str, Account] = {}
        self.payees: Dict[str, Payee] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.master_categories: Dict[str, MasterCategory] = {}
        self.categories: Dict[str, Category] = {}
        self.monthly_budgets: Dict[str, MonthlyBudget] = {}
        self.monthly_category_budgets: Dict[str, MonthlyCategoryBudget] = {}
        self.scheduled_transactions: Dict[str, ScheduledTransaction] = {}

    def parse(self) -> Budget:
        device_guid = self.device_manager.get_active_device_guid()
        yfull_path = self.device_manager.get_budget_file_path(device_guid)
        with open(yfull_path, "r") as f:
            data = json.load(f)

        # Parse simple entities
        self._parse_entities(data.get("accounts", []), Account, self.accounts)
        self._parse_entities(data.get("payees", []), Payee, self.payees)
        self._parse_entities(
            data.get("transactions", []), Transaction, self.transactions
        )
        self._parse_entities(
            data.get("monthlyBudgets", []), MonthlyBudget, self.monthly_budgets
        )
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

        self.apply_deltas()

        return Budget(
            accounts=list(self.accounts.values()),
            payees=list(self.payees.values()),
            transactions=list(self.transactions.values()),
            master_categories=list(self.master_categories.values()),
            categories=list(self.categories.values()),
            monthly_budgets=list(self.monthly_budgets.values()),
            monthly_category_budgets=list(self.monthly_category_budgets.values()),
            scheduled_transactions=list(self.scheduled_transactions.values()),
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
            if (
                "subCategories" in master_category_data
                and master_category_data["subCategories"] is not None
            ):
                for category_data in master_category_data["subCategories"]:
                    category = Category(**category_data)
                    self.categories[category.entityId] = category

            # Create master category without subCategories to avoid circular reference
            master_category_clean = {
                k: v for k, v in master_category_data.items() if k != "subCategories"
            }
            master_category = MasterCategory(**master_category_clean)
            self.master_categories[master_category.entityId] = master_category

    def _get_entity_mapping(self, entity_type):
        """Get the collection and model class for a given entity type."""
        entity_mappings = {
            # Basic entities
            "account": (self.accounts, Account),
            "payee": (self.payees, Payee),
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

    def _discover_delta_files(self) -> List[Path]:
        ydiff_files = list(self.device_dir.glob("*.ydiff"))
        return sorted(ydiff_files, key=self._get_delta_sort_key)

    def _get_delta_sort_key(self, delta_path: Path) -> int:
        start_version, _ = self._parse_delta_versions(delta_path.name)
        return self._get_version_number_from_composite(
            start_version,
            f"delta file '{delta_path.name}'"
        )

    def _get_version_number_from_composite(
        self, composite_version: str, context: str
    ) -> int:
        """Extract the version number from a composite version string using DeviceManager methods.

        Args:
            composite_version: Version string (e.g., 'A-100' or 'A-100,B-200,C-50')
            context: Context string for error messages

        Returns:
            The version number from the latest version in the composite string
        """
        try:
            latest_version = self.device_manager.get_latest_version_from_composite(
                composite_version
            )
            _, version_num = self.device_manager.parse_version_string(latest_version)
            return version_num
        except ValueError as e:
            raise ValueError(
                f"Failed to parse version number from '{composite_version}' in {context}: {e}"
            )

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
