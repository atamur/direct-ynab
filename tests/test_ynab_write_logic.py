"""Comprehensive tests for YNAB4 write logic mechanisms.

This test module validates the core YNAB4 write mechanisms:
1. Device Registration - Device GUIDs, short IDs, .ydevice files
2. Knowledge Version Tracking - Version format "A-86", increments
3. .ydiff File Generation - JSON structure, camelCase naming
4. Filename Convention - Format validation and parsing
5. .ydevice Update - Knowledge and metadata updates

Following TDD Red-Green-Refactor methodology.
"""

import json
import pytest
import uuid
from pathlib import Path
from unittest.mock import mock_open, patch
from typing import Dict, Any, List, Optional


class TestDeviceRegistration:
    """Test device registration mechanisms."""
    
    def test_generate_unique_device_guid(self):
        """Test generating unique device GUIDs."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        guid1 = device_manager.generate_device_guid()
        guid2 = device_manager.generate_device_guid()
        
        # Should generate valid UUIDs
        assert isinstance(guid1, str)
        assert isinstance(guid2, str)
        assert len(guid1) == 36  # Standard UUID length with dashes
        assert len(guid2) == 36
        
        # Should be unique
        assert guid1 != guid2
        
        # Should be valid UUID format
        uuid.UUID(guid1)  # Will raise ValueError if invalid
        uuid.UUID(guid2)
    
    def test_create_ydevice_file_structure(self):
        """Test creating proper .ydevice file structure."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        device_guid = "TEST-DEVICE-GUID-12345"
        short_id = "A"
        
        ydevice_data = device_manager.create_ydevice_structure(
            device_guid=device_guid,
            short_id=short_id,
            friendly_name="Test Device",
            knowledge="A-1"
        )
        
        # Should have all required fields
        assert ydevice_data["deviceGUID"] == device_guid
        assert ydevice_data["shortDeviceId"] == short_id
        assert ydevice_data["friendlyName"] == "Test Device"
        assert ydevice_data["knowledge"] == "A-1"
        assert ydevice_data["knowledgeInFullBudgetFile"] == "A-1"
        assert ydevice_data["hasFullKnowledge"] is False
        assert "formatVersion" in ydevice_data
        assert "YNABVersion" in ydevice_data
        assert "deviceType" in ydevice_data
    
    def test_assign_device_short_id_sequential(self):
        """Test assigning device short IDs sequentially (A, B, C, etc.)."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        # Mock existing devices
        existing_devices = []  # No existing devices
        short_id_1 = device_manager.assign_next_short_id(existing_devices)
        assert short_id_1 == "A"
        
        existing_devices = ["A"]
        short_id_2 = device_manager.assign_next_short_id(existing_devices)
        assert short_id_2 == "B"
        
        existing_devices = ["A", "B", "C"]
        short_id_4 = device_manager.assign_next_short_id(existing_devices)
        assert short_id_4 == "D"
    
    def test_register_new_device_creates_files(self, tmp_path):
        """Test registering new device creates .ydevice file."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager(budget_dir=tmp_path)
        
        # Create required directory structure
        data_dir = tmp_path / "data1~TEST"
        devices_dir = data_dir / "devices"
        devices_dir.mkdir(parents=True)
        
        device_info = device_manager.register_new_device(
            friendly_name="Test Device",
            device_type="Desktop",
            ynab_version="4.3.857"
        )
        
        # Should return device info
        assert "deviceGUID" in device_info
        assert "shortDeviceId" in device_info
        assert device_info["shortDeviceId"] == "A"  # First device
        
        # Should create .ydevice file
        ydevice_file = devices_dir / f"{device_info['shortDeviceId']}.ydevice"
        assert ydevice_file.exists()
        
        # File should contain proper structure
        with open(ydevice_file, 'r') as f:
            ydevice_data = json.load(f)
        
        assert ydevice_data["deviceGUID"] == device_info["deviceGUID"]
        assert ydevice_data["shortDeviceId"] == device_info["shortDeviceId"]
        assert ydevice_data["hasFullKnowledge"] is False
        
        # Should create device directory 
        device_dir = data_dir / device_info["deviceGUID"]
        assert device_dir.exists()
        assert device_dir.is_dir()


class TestKnowledgeVersionTracking:
    """Test knowledge version tracking mechanisms."""
    
    def test_parse_version_string_format(self):
        """Test parsing version strings in 'A-86' format."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        # Valid version strings
        device_id, version_num = device_manager.parse_version_string("A-86")
        assert device_id == "A"
        assert version_num == 86
        
        device_id, version_num = device_manager.parse_version_string("B-15")
        assert device_id == "B"
        assert version_num == 15
        
        device_id, version_num = device_manager.parse_version_string("Z-999")
        assert device_id == "Z"
        assert version_num == 999
    
    def test_parse_version_string_invalid_format(self):
        """Test parsing invalid version string formats raises errors."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        # Invalid formats should raise ValueError
        with pytest.raises(ValueError, match="Invalid version format"):
            device_manager.parse_version_string("A86")  # Missing dash
        
        with pytest.raises(ValueError, match="Invalid version format"):
            device_manager.parse_version_string("AA-86")  # Invalid device ID
        
        with pytest.raises(ValueError, match="Invalid version format"):
            device_manager.parse_version_string("A-")  # Missing version number
        
        with pytest.raises(ValueError, match="Invalid version format"):
            device_manager.parse_version_string("A-abc")  # Non-numeric version
    
    def test_increment_version_number(self):
        """Test incrementing version numbers correctly."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        next_version = device_manager.increment_version("A-86")
        assert next_version == "A-87"
        
        next_version = device_manager.increment_version("B-15")
        assert next_version == "B-16"
        
        next_version = device_manager.increment_version("A-999")
        assert next_version == "A-1000"
    
    def test_compare_version_strings(self):
        """Test comparing version strings for ordering."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        # Same device versions
        assert device_manager.compare_versions("A-86", "A-87") < 0  # A-86 < A-87
        assert device_manager.compare_versions("A-87", "A-86") > 0  # A-87 > A-86
        assert device_manager.compare_versions("A-86", "A-86") == 0  # Equal
        
        # Different devices should compare by device ID first
        assert device_manager.compare_versions("A-99", "B-1") < 0  # A < B
        assert device_manager.compare_versions("B-1", "A-99") > 0  # B > A
    
    def test_get_latest_version_across_devices(self):
        """Test finding latest version across multiple devices."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        versions = ["A-86", "B-15", "A-89", "C-2", "B-20"]
        latest = device_manager.get_latest_version(versions)
        
        # Should return the overall latest version
        assert latest == "A-89"
        
        # Test with single device
        versions = ["A-86", "A-87", "A-85"]
        latest = device_manager.get_latest_version(versions)
        assert latest == "A-87"


    def test_get_global_knowledge_from_all_devices(self, tmp_path):
        """Test calculating global knowledge from all .ydevice files."""
        from ynab_io.device_manager import DeviceManager

        # Setup test environment
        budget_dir = tmp_path / "budget"
        data_dir = budget_dir / "data1~TEST"
        devices_dir = data_dir / "devices"
        devices_dir.mkdir(parents=True)

        # Create multiple .ydevice files with different knowledge
        ydevice_a_data = {
            "deviceGUID": "GUID-A", "shortDeviceId": "A", "knowledge": "A-86"
        }
        ydevice_b_data = {
            "deviceGUID": "GUID-B", "shortDeviceId": "B", "knowledge": "B-15"
        }
        ydevice_c_data = {
            "deviceGUID": "GUID-C", "shortDeviceId": "C", "knowledge": "A-89"  # Higher version on different device
        }

        with open(devices_dir / "A.ydevice", 'w') as f:
            json.dump(ydevice_a_data, f)
        with open(devices_dir / "B.ydevice", 'w') as f:
            json.dump(ydevice_b_data, f)
        with open(devices_dir / "C.ydevice", 'w') as f:
            json.dump(ydevice_c_data, f)

        device_manager = DeviceManager(budget_dir=budget_dir)
        global_knowledge = device_manager.get_global_knowledge()

        assert global_knowledge == "A-89"

    def test_get_global_knowledge_no_devices(self, tmp_path):
        """Test get_global_knowledge returns None when no devices exist."""
        from ynab_io.device_manager import DeviceManager

        budget_dir = tmp_path / "budget"
        data_dir = budget_dir / "data1~TEST"
        devices_dir = data_dir / "devices"
        devices_dir.mkdir(parents=True)

        device_manager = DeviceManager(budget_dir=budget_dir)
        global_knowledge = device_manager.get_global_knowledge()

        assert global_knowledge is None


class TestYdiffFileGeneration:
    """Test .ydiff file generation mechanisms."""
    
    def test_create_ydiff_json_structure(self):
        """Test creating proper .ydiff JSON structure."""
        from ynab_io.writer import YnabWriter
        
        writer = YnabWriter()
        
        ydiff_data = writer.create_ydiff_structure(
            short_device_id="A",
            start_version="A-86",
            end_version="A-89",
            device_guid="TEST-DEVICE-GUID",
            data_version="4.2"
        )
        
        # Should have all required fields with correct camelCase
        assert ydiff_data["shortDeviceId"] == "A"
        assert ydiff_data["startVersion"] == "A-86"
        assert ydiff_data["endVersion"] == "A-89"
        assert ydiff_data["deviceGUID"] == "TEST-DEVICE-GUID"
        assert ydiff_data["dataVersion"] == "4.2"
        assert "publishTime" in ydiff_data
        assert "items" in ydiff_data
        assert isinstance(ydiff_data["items"], list)
    
    def test_add_entity_to_ydiff_items(self):
        """Test adding entities to .ydiff items array."""
        from ynab_io.writer import YnabWriter
        from ynab_io.models import Transaction, Account, Payee
        
        writer = YnabWriter()
        
        # Create test entities
        transaction = Transaction(
            entityId="TEST-TRANS-ID",
            accountId="TEST-ACCOUNT-ID",
            amount=100.0,
            date="2025-01-01",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-87"
        )
        
        account = Account(
            entityId="TEST-ACCOUNT-ID",
            accountName="Test Account",
            accountType="Checking",
            onBudget=True,
            sortableIndex=0,
            hidden=False,
            entityVersion="A-87"
        )
        
        # Convert entities to ydiff item format
        transaction_item = writer.entity_to_ydiff_item(transaction, "transaction")
        account_item = writer.entity_to_ydiff_item(account, "account")
        
        # Should use camelCase field names
        assert transaction_item["entityType"] == "transaction"
        assert transaction_item["entityId"] == "TEST-TRANS-ID"
        assert transaction_item["accountId"] == "TEST-ACCOUNT-ID"
        assert transaction_item["entityVersion"] == "A-87"
        assert transaction_item["isTombstone"] is False
        
        assert account_item["entityType"] == "account"
        assert account_item["accountName"] == "Test Account"
        assert account_item["onBudget"] is True
    
    def test_handle_tombstone_items_for_deletions(self):
        """Test handling tombstone entries for deletions."""
        from ynab_io.writer import YnabWriter
        
        writer = YnabWriter()
        
        tombstone_item = writer.create_tombstone_item(
            entity_id="DELETED-ENTITY-ID",
            entity_type="transaction",
            entity_version="A-88"
        )
        
        # Should mark as tombstone with minimal data
        assert tombstone_item["entityId"] == "DELETED-ENTITY-ID"
        assert tombstone_item["entityType"] == "transaction"
        assert tombstone_item["entityVersion"] == "A-88"
        assert tombstone_item["isTombstone"] is True
        
        # Should not contain entity-specific fields
        assert "amount" not in tombstone_item
        assert "accountId" not in tombstone_item
    
    def test_generate_complete_ydiff_file(self):
        """Test generating complete .ydiff file with entities."""
        from ynab_io.writer import YnabWriter
        from ynab_io.models import Transaction
        
        writer = YnabWriter()
        
        # Create test entities
        transactions = [
            Transaction(
                entityId="TRANS-1",
                accountId="ACCOUNT-1",
                amount=100.0,
                date="2025-01-01",
                cleared="Cleared",
                accepted=True,
                entityVersion="A-87"
            ),
            Transaction(
                entityId="TRANS-2",
                accountId="ACCOUNT-1",
                amount=200.0,
                date="2025-01-02",
                cleared="Uncleared",
                accepted=True,
                entityVersion="A-88"
            )
        ]
        
        ydiff_content = writer.generate_ydiff(
            entities={"transactions": transactions},
            start_version="A-86",
            end_version="A-88",
            device_info={"shortDeviceId": "A", "deviceGUID": "TEST-GUID"}
        )
        
        # Should be valid JSON
        ydiff_data = json.loads(ydiff_content)
        
        # Should have correct structure
        assert ydiff_data["startVersion"] == "A-86"
        assert ydiff_data["endVersion"] == "A-88"
        assert len(ydiff_data["items"]) == 2
        
        # Items should be properly formatted
        item1 = ydiff_data["items"][0]
        assert item1["entityType"] == "transaction"
        assert item1["entityId"] == "TRANS-1"
        assert item1["amount"] == 100.0

    def test_write_ydiff_and_update_ydevice(self, tmp_path):
        """Test writing a .ydiff file and updating the .ydevice file."""
        from ynab_io.writer import YnabWriter
        from ynab_io.device_manager import DeviceManager
        from ynab_io.models import Transaction

        # Setup test environment
        budget_dir = tmp_path / "budget"
        data_dir = budget_dir / "data1~TEST"
        device_guid = "TEST-DEVICE-GUID"
        device_dir = data_dir / device_guid
        devices_dir = data_dir / "devices"
        
        device_dir.mkdir(parents=True)
        devices_dir.mkdir(parents=True)

        # Create initial .ydevice file
        ydevice_path = devices_dir / "A.ydevice"
        device_data = {
            "deviceGUID": device_guid,
            "shortDeviceId": "A",
            "knowledge": "A-86",
            "knowledgeInFullBudgetFile": "A-86"
        }
        with open(ydevice_path, 'w') as f:
            json.dump(device_data, f)

        # Initialize managers
        device_manager = DeviceManager(budget_dir=budget_dir)
        writer = YnabWriter(device_manager=device_manager)

        # Create changes to write
        new_transaction = Transaction(
            entityId="NEW-TRANS-ID",
            accountId="ACCOUNT-1",
            amount=150.0,
            date="2025-01-01",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-87"
        )
        
        # Execute write operation using short_id
        result = writer.write_changes(
            entities={"transactions": [new_transaction]},
            current_knowledge="A-86",
            short_id="A"
        )

        # Should return success with new version info
        assert result["success"] is True
        assert result["new_version"] == "A-87"
        assert result["ydiff_filename"] == "A-86_A-87.ydiff"

        # Should create .ydiff file
        ydiff_path = device_dir / result["ydiff_filename"]
        assert ydiff_path.exists()

        # .ydiff should have correct content
        with open(ydiff_path, 'r') as f:
            ydiff_data = json.load(f)

        assert ydiff_data["startVersion"] == "A-86"
        assert ydiff_data["endVersion"] == "A-87"
        assert len(ydiff_data["items"]) == 1
        assert ydiff_data["items"][0]["entityId"] == "NEW-TRANS-ID"

        # Should update .ydevice file
        with open(ydevice_path, 'r') as f:
            updated_device_data = json.load(f)

        assert updated_device_data["knowledge"] == "A-87"


class TestFilenameConvention:
    """Test .ydiff filename convention mechanisms."""
    
    def test_generate_ydiff_filename_from_versions(self):
        """Test generating .ydiff filename from version range."""
        from ynab_io.writer import YnabWriter
        
        writer = YnabWriter()
        
        filename = writer.generate_ydiff_filename("A-86", "A-89")
        assert filename == "A-86_A-89.ydiff"
        
        filename = writer.generate_ydiff_filename("B-15", "B-20")
        assert filename == "B-15_B-20.ydiff"
        
        filename = writer.generate_ydiff_filename("A-999", "A-1000")
        assert filename == "A-999_A-1000.ydiff"
    
    def test_parse_ydiff_filename_extracts_versions(self):
        """Test parsing .ydiff filename to extract versions."""
        from ynab_io.writer import YnabWriter
        
        writer = YnabWriter()
        
        start, end = writer.parse_ydiff_filename("A-86_A-89.ydiff")
        assert start == "A-86"
        assert end == "A-89"
        
        start, end = writer.parse_ydiff_filename("B-15_B-20.ydiff")
        assert start == "B-15"
        assert end == "B-20"
    
    def test_parse_invalid_ydiff_filename_raises_error(self):
        """Test parsing invalid .ydiff filename raises ValueError."""
        from ynab_io.writer import YnabWriter
        
        writer = YnabWriter()
        
        with pytest.raises(ValueError, match="Invalid delta filename format"):
            writer.parse_ydiff_filename("invalid.ydiff")
        
        with pytest.raises(ValueError, match="Invalid delta filename format"):
            writer.parse_ydiff_filename("A-86_A-89.txt")
        
        with pytest.raises(ValueError, match="Invalid delta filename format"):
            writer.parse_ydiff_filename("A86_A89.ydiff")
    
    def test_validate_filename_format(self):
        """Test validating .ydiff filename format."""
        from ynab_io.writer import YnabWriter
        
        writer = YnabWriter()
        
        # Valid filenames
        assert writer.validate_ydiff_filename("A-86_A-89.ydiff") is True
        assert writer.validate_ydiff_filename("B-1_B-2.ydiff") is True
        assert writer.validate_ydiff_filename("Z-999_Z-1000.ydiff") is True
        
        # Invalid filenames
        assert writer.validate_ydiff_filename("invalid.ydiff") is False
        assert writer.validate_ydiff_filename("A-86_A-89.txt") is False
        assert writer.validate_ydiff_filename("A86_A89.ydiff") is False


class TestYdeviceUpdate:
    """Test .ydevice file update mechanisms."""
    
    def test_update_knowledge_after_writing_changes(self, tmp_path):
        """Test updating knowledge fields after writing changes."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        # Create test .ydevice file
        ydevice_path = tmp_path / "A.ydevice"
        initial_data = {
            "deviceGUID": "TEST-GUID",
            "shortDeviceId": "A",
            "knowledge": "A-86",
            "knowledgeInFullBudgetFile": "A-86",
            "friendlyName": "Test Device"
        }
        
        with open(ydevice_path, 'w') as f:
            json.dump(initial_data, f)
        
        # Update knowledge to new version
        device_manager.update_device_knowledge(
            ydevice_path=ydevice_path,
            new_knowledge="A-89",
            new_full_budget_knowledge="A-89"
        )
        
        # Should update the file
        with open(ydevice_path, 'r') as f:
            updated_data = json.load(f)
        
        assert updated_data["knowledge"] == "A-89"
        assert updated_data["knowledgeInFullBudgetFile"] == "A-89"
        # Other fields should remain unchanged
        assert updated_data["deviceGUID"] == "TEST-GUID"
        assert updated_data["shortDeviceId"] == "A"
        assert updated_data["friendlyName"] == "Test Device"
    
    def test_maintain_device_metadata_integrity(self, tmp_path):
        """Test maintaining device metadata integrity during updates."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        # Create test .ydevice file with all metadata
        ydevice_path = tmp_path / "A.ydevice"
        initial_data = {
            "deviceGUID": "TEST-GUID",
            "shortDeviceId": "A",
            "knowledge": "A-86",
            "knowledgeInFullBudgetFile": "A-86",
            "friendlyName": "Test Device",
            "formatVersion": "1.2",
            "YNABVersion": "4.3.857",
            "deviceType": "Desktop",
            "hasFullKnowledge": False,
            "lastDataVersionFullyKnown": "4.2"
        }
        
        with open(ydevice_path, 'w') as f:
            json.dump(initial_data, f, indent=2)
        
        # Update only knowledge
        device_manager.update_device_knowledge(
            ydevice_path=ydevice_path,
            new_knowledge="A-89"
        )
        
        # All metadata should be preserved
        with open(ydevice_path, 'r') as f:
            updated_data = json.load(f)
        
        assert updated_data["knowledge"] == "A-89"
        assert updated_data["deviceGUID"] == "TEST-GUID"
        assert updated_data["formatVersion"] == "1.2"
        assert updated_data["YNABVersion"] == "4.3.857"
        assert updated_data["deviceType"] == "Desktop"
        assert updated_data["hasFullKnowledge"] is False
    
    def test_handle_atomic_ydevice_updates(self, tmp_path):
        """Test atomic updates to .ydevice files to prevent corruption."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager()
        
        # Create test .ydevice file
        ydevice_path = tmp_path / "A.ydevice"
        initial_data = {
            "deviceGUID": "TEST-GUID",
            "shortDeviceId": "A",
            "knowledge": "A-86",
            "knowledgeInFullBudgetFile": "A-86"
        }
        
        with open(ydevice_path, 'w') as f:
            json.dump(initial_data, f)
        
        # Mock file write failure to test atomic behavior
        with patch('builtins.open', side_effect=IOError("Disk full")):
            with pytest.raises(IOError):
                device_manager.update_device_knowledge(
                    ydevice_path=ydevice_path,
                    new_knowledge="A-89"
                )
        
        # Original file should remain unchanged after failed update
        with open(ydevice_path, 'r') as f:
            data = json.load(f)
        
        assert data["knowledge"] == "A-86"  # Should not be updated
    
    def test_backup_ydevice_before_update(self, tmp_path):
        """Test creating backup of .ydevice file before updates."""
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager(create_backups=True)
        
        # Create test .ydevice file
        ydevice_path = tmp_path / "A.ydevice"
        initial_data = {
            "deviceGUID": "TEST-GUID",
            "knowledge": "A-86"
        }
        
        with open(ydevice_path, 'w') as f:
            json.dump(initial_data, f)
        
        # Update knowledge
        device_manager.update_device_knowledge(
            ydevice_path=ydevice_path,
            new_knowledge="A-89"
        )
        
        # Should create backup file
        backup_files = list(tmp_path.glob("A.ydevice.backup*"))
        assert len(backup_files) >= 1
        
        # Backup should contain original data
        with open(backup_files[0], 'r') as f:
            backup_data = json.load(f)
        
        assert backup_data["knowledge"] == "A-86"


class TestIntegratedWriteWorkflow:
    """Test integrated YNAB4 write workflow combining all mechanisms."""
    
    def test_complete_write_workflow(self, tmp_path):
        """Test complete workflow from entity changes to .ydiff and .ydevice updates."""
        from ynab_io.writer import YnabWriter
        from ynab_io.device_manager import DeviceManager
        from ynab_io.models import Transaction
        
        # Setup test environment
        budget_dir = tmp_path / "budget"
        data_dir = budget_dir / "data1~TEST"
        device_dir = data_dir / "TEST-DEVICE-GUID"
        devices_dir = data_dir / "devices"
        
        device_dir.mkdir(parents=True)
        devices_dir.mkdir(parents=True)
        
        # Create initial .ydevice file
        ydevice_path = devices_dir / "A.ydevice"
        device_data = {
            "deviceGUID": "TEST-DEVICE-GUID",
            "shortDeviceId": "A",
            "knowledge": "A-86",
            "knowledgeInFullBudgetFile": "A-86"
        }
        with open(ydevice_path, 'w') as f:
            json.dump(device_data, f)
        
        # Initialize managers
        device_manager = DeviceManager(budget_dir=budget_dir)
        writer = YnabWriter(device_manager=device_manager)
        
        # Create changes to write
        new_transaction = Transaction(
            entityId="NEW-TRANS-ID",
            accountId="ACCOUNT-1",
            amount=150.0,
            date="2025-01-01",
            cleared="Uncleared",
            accepted=True,
            entityVersion="A-87"
        )
        
        # Execute complete write workflow
        result = writer.write_changes(
            entities={"transactions": [new_transaction]},
            current_knowledge="A-86",
            short_id="A"
        )
        
        # Should return success with new version info
        assert result["success"] is True
        assert result["new_version"] == "A-87"
        assert "ydiff_filename" in result
        
        # Should create .ydiff file
        ydiff_path = device_dir / result["ydiff_filename"]
        assert ydiff_path.exists()
        
        # .ydiff should have correct content
        with open(ydiff_path, 'r') as f:
            ydiff_data = json.load(f)
        
        assert ydiff_data["startVersion"] == "A-86"
        assert ydiff_data["endVersion"] == "A-87"
        assert len(ydiff_data["items"]) == 1
        assert ydiff_data["items"][0]["entityId"] == "NEW-TRANS-ID"
        
        # Should update .ydevice file
        with open(ydevice_path, 'r') as f:
            updated_device_data = json.load(f)
        
        assert updated_device_data["knowledge"] == "A-87"
        assert updated_device_data["knowledgeInFullBudgetFile"] == "A-87"
    
    def test_handle_write_errors_gracefully(self, tmp_path):
        """Test graceful error handling during write operations."""
        from ynab_io.writer import YnabWriter
        from ynab_io.device_manager import DeviceManager
        
        device_manager = DeviceManager(budget_dir=tmp_path)
        writer = YnabWriter(device_manager=device_manager)
        
        # Try to write without proper setup
        result = writer.write_changes(
            entities={},
            current_knowledge="A-86",
            short_id="A"
        )
        
        # Should fail gracefully
        assert result["success"] is False
        assert "error" in result
        assert "Could not find" in result["error"]