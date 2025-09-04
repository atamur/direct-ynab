import json
import logging
from pathlib import Path
from typing import List, Dict

from .models import Account, Payee, Transaction, Budget

class YnabParser:
    def __init__(self, budget_path: Path):
        self.budget_path = budget_path
        self.data_dir = self._find_data_dir()
        self.device_dir = self._find_device_dir()
        self.accounts: Dict[str, Account] = {}
        self.payees: Dict[str, Payee] = {}
        self.transactions: Dict[str, Transaction] = {}

    def _find_data_dir(self) -> Path:
        for p in self.budget_path.iterdir():
            if p.is_dir() and p.name.startswith('data1~'):
                return p
        raise FileNotFoundError("Could not find data directory in budget")

    def _find_device_dir(self) -> Path:
        devices_dir = self.data_dir / 'devices'
        # For now, we assume there's only one device. A more robust implementation
        # might need to handle multiple devices.
        for p in devices_dir.iterdir():
            if p.is_file() and p.suffix == '.ydevice':
                # Read the .ydevice file to get the deviceGUID
                with open(p, 'r') as f:
                    device_data = json.load(f)
                device_guid = device_data.get('deviceGUID')
                if device_guid:
                    return self.data_dir / device_guid
        raise FileNotFoundError("Could not find device directory")

    def parse(self) -> Budget:
        yfull_path = self.device_dir / 'Budget.yfull'
        with open(yfull_path, 'r') as f:
            data = json.load(f)

        for account_data in data.get('accounts', []):
            account = Account(**account_data)
            self.accounts[account.entityId] = account

        for payee_data in data.get('payees', []):
            payee = Payee(**payee_data)
            self.payees[payee.entityId] = payee

        for transaction_data in data.get('transactions', []):
            transaction = Transaction(**transaction_data)
            self.transactions[transaction.entityId] = transaction
        
        self.apply_deltas()
        
        return Budget(
            accounts=list(self.accounts.values()),
            payees=list(self.payees.values()),
            transactions=list(self.transactions.values())
        )

    def apply_deltas(self):
        delta_files = self._discover_delta_files()
        for delta_file in delta_files:
            self._apply_delta(delta_file)

    def _discover_delta_files(self) -> List[Path]:
        ydiff_files = list(self.device_dir.glob("*.ydiff"))
        return sorted(ydiff_files, key=self._get_delta_sort_key)

    def _get_delta_sort_key(self, delta_path: Path) -> int:
        start_version, _ = self._parse_delta_versions(delta_path.name)
        return int(start_version.split('-')[1])

    def _parse_delta_versions(self, filename: str) -> tuple[str, str]:
        if not filename.endswith('.ydiff'):
            raise ValueError(f"Invalid delta filename format: {filename}")
        base_name = filename[:-6]
        try:
            start_version, end_version = base_name.split('_')
        except ValueError:
            raise ValueError(f"Invalid delta filename format: {filename}")
        return start_version, end_version

    def _apply_delta(self, delta_file: Path):
        with open(delta_file, 'r') as f:
            delta_data = json.load(f)

        for item in delta_data.get('items', []):
            entity_id = item['entityId']
            entity_type = item['entityType']

            if entity_type == 'account':
                collection = self.accounts
                model = Account
            elif entity_type == 'payee':
                collection = self.payees
                model = Payee
            elif entity_type == 'transaction':
                collection = self.transactions
                model = Transaction
            else:
                logging.warning(f"Unknown entity type '{entity_type}' encountered in delta file.")
                continue

            if item['isTombstone']:
                if entity_id in collection:
                    del collection[entity_id]
                continue

            if entity_id in collection:
                existing_entity = collection[entity_id]
                existing_version = int(existing_entity.entityVersion.split('-')[1])
                new_version = int(item['entityVersion'].split('-')[1])
                if new_version > existing_version:
                    updated_data = existing_entity.model_dump()
                    updated_data.update(item)
                    collection[entity_id] = model(**updated_data)
            else:
                collection[entity_id] = model(**item)
