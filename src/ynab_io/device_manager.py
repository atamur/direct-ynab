"""Device registration and knowledge tracking for YNAB4 budgets.

This module handles:
- Device GUID generation and registration
- .ydevice file creation and management
- Knowledge version tracking and updates
- Device short ID assignment (A, B, C, etc.)
"""

import json
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime


# Constants for YNAB4 device management
DEFAULT_YNAB_VERSION = "Desktop version: YNAB 4 v4.3.857"
DEFAULT_DEVICE_TYPE = "Desktop (Test)"
DEFAULT_FORMAT_VERSION = "1.2"
DEFAULT_DATA_VERSION = "4.2"
VERSION_PATTERN = re.compile(r'^([A-Z])-(\d+)$')
MAX_DEVICE_COUNT = 26  # A-Z


class DeviceManager:
    """Manages YNAB4 device registration and knowledge tracking."""
    
    def __init__(self, budget_dir: Optional[Path] = None, create_backups: bool = False):
        """Initialize DeviceManager.
        
        Args:
            budget_dir: Path to YNAB4 budget directory
            create_backups: Whether to create backups before updates
        """
        self.budget_dir = budget_dir
        self.create_backups = create_backups
    
    def generate_device_guid(self) -> str:
        """Generate a unique device GUID.
        
        Returns:
            String representation of UUID4
        """
        return str(uuid.uuid4()).upper()
    
    def create_ydevice_structure(self, device_guid: str, short_id: str, 
                               friendly_name: str, knowledge: str,
                               knowledge_in_full: Optional[str] = None,
                               ynab_version: str = DEFAULT_YNAB_VERSION,
                               device_type: str = DEFAULT_DEVICE_TYPE,
                               format_version: str = DEFAULT_FORMAT_VERSION,
                               data_version: str = DEFAULT_DATA_VERSION) -> Dict[str, Any]:
        """Create .ydevice file structure.
        
        Args:
            device_guid: Unique device identifier
            short_id: Single character device ID (A, B, C, etc.)
            friendly_name: Human-readable device name
            knowledge: Current knowledge version (e.g., "A-1")
            knowledge_in_full: Knowledge in full budget file (defaults to knowledge)
            ynab_version: YNAB application version
            device_type: Type of device
            format_version: File format version
            data_version: Data format version
        
        Returns:
            Dictionary with .ydevice file structure
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not device_guid or not isinstance(device_guid, str):
            raise ValueError("device_guid must be a non-empty string")
        
        if not short_id or not isinstance(short_id, str) or len(short_id) != 1:
            raise ValueError("short_id must be a single character")
        
        if not friendly_name or not isinstance(friendly_name, str):
            raise ValueError("friendly_name must be a non-empty string")
        
        # Validate knowledge format
        self.parse_version_string(knowledge)  # Will raise if invalid
        
        if knowledge_in_full is None:
            knowledge_in_full = knowledge
        else:
            self.parse_version_string(knowledge_in_full)  # Validate format
            
        return {
            "deviceGUID": device_guid,
            "shortDeviceId": short_id,
            "friendlyName": friendly_name,
            "knowledge": knowledge,
            "knowledgeInFullBudgetFile": knowledge_in_full,
            "hasFullKnowledge": False,
            "formatVersion": format_version,
            "YNABVersion": ynab_version,
            "deviceType": device_type,
            "lastDataVersionFullyKnown": data_version,
            "highestDataVersionImported": None
        }
    
    def assign_next_short_id(self, existing_ids: List[str]) -> str:
        """Assign next available short device ID.
        
        Args:
            existing_ids: List of already assigned short IDs
        
        Returns:
            Next available single character ID (A, B, C, etc.)
        
        Raises:
            ValueError: If all device IDs (A-Z) are taken
        """
        if len(existing_ids) >= MAX_DEVICE_COUNT:
            raise ValueError(f"Maximum device count ({MAX_DEVICE_COUNT}) exceeded")
        
        for i in range(MAX_DEVICE_COUNT):
            short_id = chr(ord('A') + i)
            if short_id not in existing_ids:
                return short_id
        
        raise ValueError(f"No available device IDs (A-Z all taken)")
    
    def register_new_device(self, friendly_name: str, device_type: str = "Desktop", 
                          ynab_version: str = "4.3.857") -> Dict[str, str]:
        """Register a new device and create .ydevice file.
        
        Args:
            friendly_name: Human-readable device name
            device_type: Type of device
            ynab_version: YNAB application version
        
        Returns:
            Dictionary with device information (deviceGUID, shortDeviceId)
        """
        if not self.budget_dir:
            raise ValueError("Budget directory not set")
        
        # Find data directory
        data_dirs = list(self.budget_dir.glob("data1~*"))
        if not data_dirs:
            raise FileNotFoundError("Could not find data directory in budget")
        
        data_dir = data_dirs[0]
        devices_dir = data_dir / "devices"
        
        if not devices_dir.exists():
            devices_dir.mkdir(parents=True)
        
        # Find existing devices
        existing_ids = []
        for ydevice_file in devices_dir.glob("*.ydevice"):
            device_id = ydevice_file.stem
            existing_ids.append(device_id)
        
        # Generate new device info
        device_guid = self.generate_device_guid()
        short_id = self.assign_next_short_id(existing_ids)
        
        # Create device directory
        device_dir = data_dir / device_guid
        device_dir.mkdir(exist_ok=True)
        
        # Create .ydevice file
        ydevice_data = self.create_ydevice_structure(
            device_guid=device_guid,
            short_id=short_id,
            friendly_name=friendly_name,
            knowledge=f"{short_id}-1",
            ynab_version=f"Desktop version: YNAB 4 v{ynab_version}",
            device_type=f"{device_type} (Test)"
        )
        
        ydevice_path = devices_dir / f"{short_id}.ydevice"
        with open(ydevice_path, 'w') as f:
            json.dump(ydevice_data, f, indent=2)
        
        return {
            "deviceGUID": device_guid,
            "shortDeviceId": short_id
        }
    
    def parse_version_string(self, version_str: str) -> Tuple[str, int]:
        """Parse version string in 'A-86' format.
        
        Args:
            version_str: Version string like "A-86"
        
        Returns:
            Tuple of (device_id, version_number)
        
        Raises:
            ValueError: If format is invalid
        """
        if not isinstance(version_str, str):
            raise ValueError(f"Version string must be a string, got {type(version_str)}")
        
        match = VERSION_PATTERN.match(version_str)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
        
        device_id = match.group(1)
        version_num = int(match.group(2))
        
        return device_id, version_num
    
    def increment_version(self, version_str: str) -> str:
        """Increment version number.
        
        Args:
            version_str: Current version like "A-86"
        
        Returns:
            Next version like "A-87"
        """
        device_id, version_num = self.parse_version_string(version_str)
        return f"{device_id}-{version_num + 1}"
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
        
        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        device1, num1 = self.parse_version_string(version1)
        device2, num2 = self.parse_version_string(version2)
        
        # Compare device IDs first, then version numbers
        if device1 < device2:
            return -1
        elif device1 > device2:
            return 1
        else:
            if num1 < num2:
                return -1
            elif num1 > num2:
                return 1
            else:
                return 0
    
    def get_latest_version(self, versions: List[str]) -> str:
        """Get the latest version from a list.
        
        Args:
            versions: List of version strings
        
        Returns:
            Latest version string
        """
        if not versions:
            raise ValueError("Version list cannot be empty")
        
        def version_sort_key(version_str: str):
            device_id, version_num = self.parse_version_string(version_str)
            # Sort by version number first, then device ID
            return (version_num, device_id)
        
        return max(versions, key=version_sort_key)
    
    def update_device_knowledge(self, ydevice_path: Path, new_knowledge: str,
                              new_full_budget_knowledge: Optional[str] = None) -> None:
        """Update device knowledge in .ydevice file.
        
        Args:
            ydevice_path: Path to .ydevice file
            new_knowledge: New knowledge version
            new_full_budget_knowledge: New full budget knowledge (defaults to new_knowledge)
        """
        if new_full_budget_knowledge is None:
            new_full_budget_knowledge = new_knowledge
        
        # Create backup if requested
        if self.create_backups:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = ydevice_path.with_suffix(f'.ydevice.backup_{timestamp}')
            backup_path.write_bytes(ydevice_path.read_bytes())
        
        # Read current data
        with open(ydevice_path, 'r') as f:
            device_data = json.load(f)
        
        # Update knowledge fields
        device_data["knowledge"] = new_knowledge
        device_data["knowledgeInFullBudgetFile"] = new_full_budget_knowledge
        
        # Write atomically by using temporary file
        temp_path = ydevice_path.with_suffix('.ydevice.tmp')
        try:
            with open(temp_path, 'w') as f:
                json.dump(device_data, f, indent=2)
            
            # Atomic rename
            temp_path.replace(ydevice_path)
        except Exception:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise