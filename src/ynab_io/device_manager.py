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

    def _get_data_dir(self) -> Path:
        if not self.budget_dir:
            raise ValueError("Budget directory not set")
        for p in self.budget_dir.iterdir():
            if p.is_dir() and p.name.startswith('data1~'):
                return p
        raise FileNotFoundError("Could not find data directory in budget")

    def _get_devices_dir(self) -> Path:
        data_dir = self._get_data_dir()
        devices_dir = data_dir / "devices"
        if not devices_dir.exists():
            raise FileNotFoundError("Could not find devices directory")
        return devices_dir

    def _get_ydevice_file_path(self, short_id: str) -> Path:
        devices_dir = self._get_devices_dir()
        ydevice_path = devices_dir / f"{short_id}.ydevice"
        if not ydevice_path.exists():
            raise FileNotFoundError(f"Could not find .ydevice file for short_id {short_id}")
        return ydevice_path

    def get_ydevice_file_path(self, short_id: str) -> Path:
        """Get path to .ydevice file for given short ID.
        
        Args:
            short_id: Short device ID
            
        Returns:
            Path to the .ydevice file
        """
        return self._get_ydevice_file_path(short_id)

    def get_device_guid(self, short_id: str) -> str:
        ydevice_path = self._get_ydevice_file_path(short_id)
        with open(ydevice_path, 'r') as f:
            device_data = json.load(f)
        device_guid = device_data.get('deviceGUID')
        if not device_guid:
            raise ValueError(f"deviceGUID not found in {ydevice_path}")
        return device_guid

    def get_active_device_guid(self) -> str:
        """Get active device GUID based on latest knowledge version.
        
        Returns:
            Device GUID of the device with the latest knowledge
        """
        device_knowledges = self._collect_device_knowledges()
        
        if device_knowledges:
            return self._find_device_with_latest_knowledge(device_knowledges)
        
        return self._get_fallback_device_guid()

    def _collect_device_knowledges(self) -> Dict[str, str]:
        """Collect knowledge versions from all valid .ydevice files.
        
        Returns:
            Dictionary mapping device GUIDs to their knowledge versions
        """
        devices_dir = self._get_devices_dir()
        device_knowledges = {}
        
        for p in devices_dir.iterdir():
            if p.is_file() and p.suffix == '.ydevice':
                try:
                    with open(p, 'r') as f:
                        device_data = json.load(f)
                    
                    device_guid = device_data.get('deviceGUID')
                    knowledge = device_data.get('knowledge')
                    
                    if device_guid and knowledge:
                        device_knowledges[device_guid] = knowledge
                except (json.JSONDecodeError, IOError):
                    # Skip corrupted device files
                    continue
        
        return device_knowledges

    def _find_device_with_latest_knowledge(self, device_knowledges: Dict[str, str]) -> str:
        """Find the device GUID with the latest knowledge version.
        
        Args:
            device_knowledges: Dictionary mapping device GUIDs to knowledge versions
            
        Returns:
            Device GUID with the latest knowledge
        """
        latest_knowledge = self.get_latest_version(list(device_knowledges.values()))
        
        # Compare the latest version from each knowledge string with the overall latest
        for device_guid, knowledge in device_knowledges.items():
            knowledge_latest = self.get_latest_version_from_composite(knowledge)
            if knowledge_latest == latest_knowledge:
                return device_guid
        
        # This should never happen given the input, but fallback for safety
        return next(iter(device_knowledges.keys()))

    def _get_fallback_device_guid(self) -> str:
        """Get fallback device GUID when no valid knowledge versions found.
        
        Returns:
            First available device GUID
            
        Raises:
            FileNotFoundError: If no .ydevice files found
        """
        devices_dir = self._get_devices_dir()
        
        for p in devices_dir.iterdir():
            if p.is_file() and p.suffix == '.ydevice':
                return self.get_device_guid(p.stem)
        
        raise FileNotFoundError("Could not find any .ydevice file")

    def get_data_dir_path(self) -> Path:
        """Get path to data directory (data1~*).
        
        Returns:
            Path to the data directory
        """
        return self._get_data_dir()

    def get_devices_dir_path(self) -> Path:
        """Get path to devices directory.
        
        Returns:
            Path to the devices directory
        """
        return self._get_devices_dir()

    def get_device_dir_path(self, device_guid: str) -> Path:
        """Get path to specific device directory by GUID.
        
        Args:
            device_guid: Device GUID
            
        Returns:
            Path to the device directory
        """
        data_dir = self.get_data_dir_path()
        device_dir = data_dir / device_guid
        if not device_dir.exists():
            raise FileNotFoundError(f"Could not find device directory for GUID {device_guid}")
        return device_dir

    def get_budget_file_path(self, device_guid: str) -> Path:
        """Get path to Budget.yfull file for given device GUID.
        
        Args:
            device_guid: Device GUID
            
        Returns:
            Path to the Budget.yfull file
        """
        device_dir = self.get_device_dir_path(device_guid)
        budget_file = device_dir / "Budget.yfull"
        return budget_file
    
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
        devices_dir = self._get_devices_dir()
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
        data_dir = self._get_data_dir()
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
    
    def parse_composite_knowledge_string(self, composite_str: str) -> List[Tuple[str, int]]:
        """Parse composite knowledge string like 'A-11429,B-63,C-52'.
        
        Handles both single version strings (e.g., 'A-86') and composite 
        knowledge strings with multiple device versions separated by commas.
        
        Args:
            composite_str: Knowledge string, either single ('A-86') or 
                          composite ('A-11429,B-63,C-52')
            
        Returns:
            List of (device_id, version_number) tuples sorted by device_id
            
        Raises:
            ValueError: If composite_str is not a string or any version is invalid
            
        Examples:
            >>> dm = DeviceManager()
            >>> dm.parse_composite_knowledge_string("A-86")
            [('A', 86)]
            >>> dm.parse_composite_knowledge_string("A-11429,B-63,C-52")
            [('A', 11429), ('B', 63), ('C', 52)]
        """
        if not isinstance(composite_str, str):
            raise ValueError(f"Knowledge string must be a string, got {type(composite_str)}")
        
        composite_str = composite_str.strip()
        if not composite_str:
            raise ValueError("Knowledge string cannot be empty")
        
        if ',' not in composite_str:
            # Single version string
            device_id, version_num = self.parse_version_string(composite_str)
            return [(device_id, version_num)]
        
        # Split by comma and parse each version
        version_parts = [part.strip() for part in composite_str.split(',') if part.strip()]
        if not version_parts:
            raise ValueError("No valid version parts found in composite knowledge string")
        
        parsed_versions = []
        for version_part in version_parts:
            try:
                device_id, version_num = self.parse_version_string(version_part)
                parsed_versions.append((device_id, version_num))
            except ValueError as e:
                raise ValueError(f"Invalid version part '{version_part}' in composite string: {e}")
        
        return parsed_versions

    def get_latest_version_from_composite(self, composite_str: str) -> str:
        """Get the latest version from a composite knowledge string.
        
        For composite strings like 'A-11429,B-63,C-52', returns the version
        with the highest version number. If version numbers are equal,
        sorts by device ID alphabetically.
        
        Args:
            composite_str: Knowledge string, single or composite format
            
        Returns:
            Latest version string in the format 'A-86'
            
        Examples:
            >>> dm = DeviceManager()
            >>> dm.get_latest_version_from_composite("A-86")
            'A-86'
            >>> dm.get_latest_version_from_composite("A-11429,B-63,C-52")
            'A-11429'
        """
        parsed_versions = self.parse_composite_knowledge_string(composite_str)
        
        # Find the version with the highest version number, then by device ID
        latest_version = max(parsed_versions, key=lambda x: (x[1], x[0]))
        return f"{latest_version[0]}-{latest_version[1]}"

    def get_latest_version(self, versions: List[str]) -> str:
        """Get the latest version from a list of knowledge strings.
        
        Processes both single version strings and composite knowledge strings,
        extracting the highest version number across all inputs.
        
        Args:
            versions: List of knowledge strings (single or composite format)
        
        Returns:
            Latest version string in format 'A-86'
            
        Raises:
            ValueError: If versions list is empty or contains invalid strings
            
        Examples:
            >>> dm = DeviceManager()
            >>> dm.get_latest_version(["A-86", "B-100"])
            'B-100'
            >>> dm.get_latest_version(["A-86", "A-11429,B-63", "B-100"])
            'A-11429'
        """
        if not versions:
            raise ValueError("Version list cannot be empty")
        
        # Extract the latest version from each knowledge string
        all_latest_versions = []
        for version_str in versions:
            try:
                latest_from_this_str = self.get_latest_version_from_composite(version_str)
                all_latest_versions.append(latest_from_this_str)
            except ValueError as e:
                raise ValueError(f"Invalid version string '{version_str}': {e}")
        
        # Find the overall latest version using consistent sorting logic
        def version_sort_key(version_str: str):
            device_id, version_num = self.parse_version_string(version_str)
            return (version_num, device_id)
        
        return max(all_latest_versions, key=version_sort_key)

    def get_global_knowledge(self) -> Optional[str]:
        """Calculate global knowledge from all .ydevice files.

        Returns:
            Latest knowledge version string or None if no devices found
        """
        try:
            devices_dir = self._get_devices_dir()
        except FileNotFoundError:
            return None

        all_knowledges = []
        for ydevice_file in devices_dir.glob("*.ydevice"):
            try:
                with open(ydevice_file, 'r') as f:
                    ydevice_data = json.load(f)
                
                if "knowledge" in ydevice_data:
                    all_knowledges.append(ydevice_data["knowledge"])
            except (json.JSONDecodeError, IOError):
                # Ignore corrupted or unreadable files
                continue
        
        if not all_knowledges:
            return None
            
        return self.get_latest_version(all_knowledges)
    
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