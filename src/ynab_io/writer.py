"""YNAB4 delta file (.ydiff) generation and writing.

This module handles:
- .ydiff file generation with proper JSON structure
- Entity serialization with camelCase naming conventions
- Filename generation and parsing for delta files
- Tombstone handling for deletions
- Integration with DeviceManager for complete write workflows
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime

from .models import Account, Payee, Transaction, Budget
from .device_manager import DeviceManager


# Constants for YNAB4 .ydiff files
DEFAULT_DATA_VERSION = "4.2"
YDIFF_EXTENSION = ".ydiff"
YDIFF_FILENAME_PATTERN = re.compile(r"^([A-Z]-\d+)_([A-Z]-\d+)\.ydiff")


class YnabWriter:
    """Handles YNAB4 delta file generation and writing."""

    def __init__(self, device_manager: Optional[DeviceManager] = None):
        """Initialize YnabWriter.

        Args:
            device_manager: DeviceManager instance for complete workflows
        """
        self.device_manager = device_manager

    def create_ydiff_structure(
        self,
        short_device_id: str,
        start_version: str,
        end_version: str,
        device_guid: str,
        data_version: str = DEFAULT_DATA_VERSION,
    ) -> Dict[str, Any]:
        """Create base .ydiff JSON structure.

        Args:
            short_device_id: Device short ID (A, B, C, etc.)
            start_version: Starting version (e.g., "A-86")
            end_version: Ending version (e.g., "A-89")
            device_guid: Device GUID
            data_version: Data format version

        Returns:
            Dictionary with .ydiff file structure
        """
        publish_time = datetime.now().strftime("%a %b %d %H:%M:%S GMT%z %Y")

        return {
            "shortDeviceId": short_device_id,
            "startVersion": start_version,
            "endVersion": end_version,
            "deviceGUID": device_guid,
            "publishTime": publish_time,
            "budgetDataGUID": None,
            "formatVersion": None,
            "dataVersion": data_version,
            "items": [],
        }

    def entity_to_ydiff_item(
        self,
        entity: Union[Account, Payee, Transaction],
        entity_type: str,
        is_tombstone: bool = False,
    ) -> Dict[str, Any]:
        """Convert entity to .ydiff item format.

        Args:
            entity: Entity instance (Account, Payee, or Transaction)
            entity_type: Type name ("account", "payee", "transaction")
            is_tombstone: Whether this is a deletion (tombstone)

        Returns:
            Dictionary in .ydiff item format with camelCase fields
        """
        # Base item structure
        item = self._create_base_ydiff_item(entity, entity_type, is_tombstone)

        if is_tombstone:
            return item

        # Add entity-specific fields based on type
        entity_serializers = {
            "transaction": self._serialize_transaction,
            "account": self._serialize_account,
            "payee": self._serialize_payee,
        }

        serializer = entity_serializers.get(entity_type)
        if serializer:
            item.update(serializer(entity))

        return item

    def _create_base_ydiff_item(
        self,
        entity: Union[Account, Payee, Transaction],
        entity_type: str,
        is_tombstone: bool,
    ) -> Dict[str, Any]:
        """Create base .ydiff item structure."""
        return {
            "entityType": entity_type,
            "entityId": entity.entityId,
            "entityVersion": entity.entityVersion,
            "isTombstone": is_tombstone,
            "madeWithKnowledge": None,
            "isResolvedConflict": False,
        }

    def _serialize_transaction(self, transaction: Transaction) -> Dict[str, Any]:
        """Serialize transaction entity to .ydiff format."""
        data = {
            "accountId": transaction.accountId,
            "date": transaction.date,
            "amount": transaction.amount,
            "cleared": transaction.cleared,
            "accepted": transaction.accepted,
        }
        if transaction.memo is not None:
            data["memo"] = transaction.memo
        return data

    def _serialize_account(self, account: Account) -> Dict[str, Any]:
        """Serialize account entity to .ydiff format."""
        return {
            "accountName": account.accountName,
            "accountType": account.accountType,
            "onBudget": account.onBudget,
            "sortableIndex": account.sortableIndex,
            "hidden": account.hidden,
        }

    def _serialize_payee(self, payee: Payee) -> Dict[str, Any]:
        """Serialize payee entity to .ydiff format."""
        return {"name": payee.name, "enabled": payee.enabled}

    def create_tombstone_item(
        self, entity_id: str, entity_type: str, entity_version: str
    ) -> Dict[str, Any]:
        """Create a tombstone (deletion) item.

        Args:
            entity_id: ID of deleted entity
            entity_type: Type of entity ("account", "payee", "transaction")
            entity_version: Version of the deletion

        Returns:
            Tombstone item dictionary
        """
        return {
            "entityType": entity_type,
            "entityId": entity_id,
            "entityVersion": entity_version,
            "isTombstone": True,
            "madeWithKnowledge": None,
            "isResolvedConflict": False,
        }

    def generate_ydiff(
        self,
        entities: Dict[str, List],
        start_version: str,
        end_version: str,
        device_info: Dict[str, str],
    ) -> str:
        """Generate complete .ydiff file content.

        Args:
            entities: Dictionary with entity lists (e.g., {"transactions": [...]})
            start_version: Starting version
            end_version: Ending version
            device_info: Device information (shortDeviceId, deviceGUID)

        Returns:
            JSON string of .ydiff content
        """
        ydiff_data = self.create_ydiff_structure(
            short_device_id=device_info["shortDeviceId"],
            start_version=start_version,
            end_version=end_version,
            device_guid=device_info["deviceGUID"],
        )

        # Add entities to items array
        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                # Map plural types to singular
                singular_type = entity_type.rstrip("s")  # transactions -> transaction
                item = self.entity_to_ydiff_item(entity, singular_type)
                ydiff_data["items"].append(item)

        return json.dumps(ydiff_data, indent=2)

    def generate_ydiff_filename(self, start_version: str, end_version: str) -> str:
        """Generate .ydiff filename from version range.

        Args:
            start_version: Starting version (e.g., "A-86")
            end_version: Ending version (e.g., "A-89")

        Returns:
            Filename like "A-86_A-89.ydiff"
        """
        return f"{start_version}_{end_version}{YDIFF_EXTENSION}"

    def parse_ydiff_filename(self, filename: str) -> Tuple[str, str]:
        """Parse .ydiff filename to extract versions.

        Args:
            filename: .ydiff filename

        Returns:
            Tuple of (start_version, end_version)

        Raises:
            ValueError: If filename format is invalid
        """
        if not isinstance(filename, str):
            raise ValueError(f"Filename must be a string, got {type(filename)}")

        if not filename.endswith(YDIFF_EXTENSION):
            raise ValueError(f"Invalid delta filename format: {filename}")

        match = YDIFF_FILENAME_PATTERN.match(filename)
        if not match:
            raise ValueError(f"Invalid delta filename format: {filename}")

        return match.group(1), match.group(2)

    def validate_ydiff_filename(self, filename: str) -> bool:
        """Validate .ydiff filename format.

        Args:
            filename: Filename to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            self.parse_ydiff_filename(filename)
            return True
        except ValueError:
            return False

    def write_changes(
        self, entities: Dict[str, List], current_knowledge: str, short_id: str
    ) -> Dict[str, Any]:
        """Write entity changes to .ydiff file and update .ydevice.

        Args:
            entities: Dictionary with entity changes
            current_knowledge: Current knowledge version
            short_id: The short id of the device

        Returns:
            Dictionary with result information
        """
        if not self.device_manager:
            return {"success": False, "error": "DeviceManager not available"}

        try:
            # Determine new version
            new_version = self.device_manager.increment_version(current_knowledge)

            device_guid = self.device_manager.get_device_guid(short_id)
            # Find device info from existing .ydevice files
            device_info = {"shortDeviceId": short_id, "deviceGUID": device_guid}

            # Generate .ydiff content
            ydiff_content = self.generate_ydiff(
                entities=entities,
                start_version=current_knowledge,
                end_version=new_version,
                device_info=device_info,
            )

            # Generate filename
            ydiff_filename = self.generate_ydiff_filename(
                current_knowledge, new_version
            )

            # Write .ydiff file
            device_dir = self.device_manager.get_device_dir_path(device_guid)
            ydiff_path = device_dir / ydiff_filename
            with open(ydiff_path, "w") as f:
                f.write(ydiff_content)

            # Update .ydevice file
            ydevice_path = self.device_manager.get_ydevice_file_path(short_id)
            self.device_manager.update_device_knowledge(
                ydevice_path=ydevice_path, new_knowledge=new_version
            )

            return {
                "success": True,
                "new_version": new_version,
                "ydiff_filename": ydiff_filename,
            }

        except (FileNotFoundError, ValueError, IOError) as e:
            return {"success": False, "error": str(e)}
