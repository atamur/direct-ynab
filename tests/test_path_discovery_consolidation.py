"""Streamlined tests for consolidated path discovery logic.

This test module validates unique aspects of path discovery consolidation:
1. DeviceManager has complete API for path discovery
2. Path discovery methods are consistent and deterministic
3. Required path discovery methods exist

These tests complement existing parser, writer, and integration tests
rather than duplicating their coverage.
"""

import json
import pytest
from pathlib import Path

from ynab_io.device_manager import DeviceManager
from ynab_io.parser import YnabParser
from ynab_io.writer import YnabWriter


class TestPathDiscoveryConsolidation:
    """Test that all path discovery is centralized in DeviceManager."""

    def test_device_manager_has_all_path_discovery_methods(self, tmp_path):
        """Test that DeviceManager provides all necessary path discovery methods."""
        device_manager = DeviceManager(budget_dir=tmp_path)

        # Create required directory structure
        data_dir = tmp_path / "data1~TEST"
        devices_dir = data_dir / "devices"
        test_device_guid = "TEST-DEVICE-GUID-12345"
        device_dir = data_dir / test_device_guid

        data_dir.mkdir()
        devices_dir.mkdir()
        device_dir.mkdir()

        # Create a test .ydevice file
        ydevice_file = devices_dir / "A.ydevice"
        ydevice_data = {
            "deviceGUID": test_device_guid,
            "shortDeviceId": "A",
            "knowledge": "A-1",
        }
        with open(ydevice_file, "w") as f:
            json.dump(ydevice_data, f)

        # Test all path discovery methods exist and work
        assert hasattr(device_manager, "get_data_dir_path")
        assert hasattr(device_manager, "get_device_dir_path")
        assert hasattr(device_manager, "get_ydevice_file_path")
        assert hasattr(device_manager, "get_devices_dir_path")
        assert hasattr(device_manager, "get_budget_file_path")

        # Test methods return correct paths
        assert device_manager.get_data_dir_path() == data_dir
        assert device_manager.get_devices_dir_path() == devices_dir
        assert device_manager.get_device_dir_path(test_device_guid) == device_dir
        assert device_manager.get_ydevice_file_path("A") == ydevice_file
        assert (
            device_manager.get_budget_file_path(test_device_guid)
            == device_dir / "Budget.yfull"
        )


class TestPathDiscoveryConsistency:
    """Test that path discovery is consistent across all methods."""

    def test_all_path_methods_use_same_base_directories(self, tmp_path):
        """Test all path discovery methods use consistent base directories."""
        device_manager = DeviceManager(budget_dir=tmp_path)

        # Create directory structure
        data_dir = tmp_path / "data1~TEST"
        devices_dir = data_dir / "devices"
        test_device_guid = "TEST-DEVICE-GUID-12345"
        device_dir = data_dir / test_device_guid

        data_dir.mkdir()
        devices_dir.mkdir()
        device_dir.mkdir()

        # Create .ydevice file
        ydevice_file = devices_dir / "A.ydevice"
        ydevice_data = {
            "deviceGUID": test_device_guid,
            "shortDeviceId": "A",
            "knowledge": "A-1",
        }
        with open(ydevice_file, "w") as f:
            json.dump(ydevice_data, f)

        # All methods should use same base directories
        discovered_data_dir = device_manager.get_data_dir_path()
        discovered_devices_dir = device_manager.get_devices_dir_path()
        discovered_device_dir = device_manager.get_device_dir_path(test_device_guid)
        discovered_ydevice_file = device_manager.get_ydevice_file_path("A")
        discovered_budget_file = device_manager.get_budget_file_path(test_device_guid)

        # Check consistency
        assert discovered_data_dir == data_dir
        assert discovered_devices_dir == devices_dir
        assert discovered_device_dir == device_dir
        assert discovered_ydevice_file == ydevice_file
        assert discovered_budget_file == device_dir / "Budget.yfull"
        assert discovered_device_dir.parent == discovered_data_dir
        assert discovered_ydevice_file.parent == devices_dir
        assert discovered_devices_dir.parent == discovered_data_dir

    def test_path_discovery_methods_are_deterministic(self, tmp_path):
        """Test that path discovery methods return consistent results."""
        device_manager = DeviceManager(budget_dir=tmp_path)

        # Create directory structure
        data_dir = tmp_path / "data1~TEST"
        devices_dir = data_dir / "devices"
        test_device_guid = "TEST-DEVICE-GUID-12345"
        device_dir = data_dir / test_device_guid

        data_dir.mkdir()
        devices_dir.mkdir()
        device_dir.mkdir()

        # Create .ydevice file
        ydevice_file = devices_dir / "A.ydevice"
        ydevice_data = {
            "deviceGUID": test_device_guid,
            "shortDeviceId": "A",
            "knowledge": "A-1",
        }
        with open(ydevice_file, "w") as f:
            json.dump(ydevice_data, f)

        # Multiple calls should return same results
        data_dir_1 = device_manager.get_data_dir_path()
        data_dir_2 = device_manager.get_data_dir_path()
        assert data_dir_1 == data_dir_2

        devices_dir_1 = device_manager.get_devices_dir_path()
        devices_dir_2 = device_manager.get_devices_dir_path()
        assert devices_dir_1 == devices_dir_2

        device_dir_1 = device_manager.get_device_dir_path(test_device_guid)
        device_dir_2 = device_manager.get_device_dir_path(test_device_guid)
        assert device_dir_1 == device_dir_2

        ydevice_file_1 = device_manager.get_ydevice_file_path("A")
        ydevice_file_2 = device_manager.get_ydevice_file_path("A")
        assert ydevice_file_1 == ydevice_file_2

        budget_file_1 = device_manager.get_budget_file_path(test_device_guid)
        budget_file_2 = device_manager.get_budget_file_path(test_device_guid)
        assert budget_file_1 == budget_file_2


class TestRequiredPathDiscoveryMethods:
    """Test that required path discovery methods exist for consolidation."""

    def test_device_manager_has_budget_file_path_method(self, tmp_path):
        """Test that DeviceManager has method to get Budget.yfull path."""
        device_manager = DeviceManager(budget_dir=tmp_path)

        # Create directory structure
        data_dir = tmp_path / "data1~TEST"
        test_device_guid = "TEST-DEVICE-GUID-12345"
        device_dir = data_dir / test_device_guid
        device_dir.mkdir(parents=True)

        budget_file = device_dir / "Budget.yfull"
        budget_file.write_text("{}")

        # Method should exist and work correctly
        budget_path = device_manager.get_budget_file_path(test_device_guid)
        assert budget_path == budget_file

    def test_device_manager_has_devices_dir_path_method(self, tmp_path):
        """Test that DeviceManager has public method to get devices directory."""
        device_manager = DeviceManager(budget_dir=tmp_path)

        # Create directory structure
        data_dir = tmp_path / "data1~TEST"
        devices_dir = data_dir / "devices"
        devices_dir.mkdir(parents=True)

        # Method should exist and work correctly
        devices_path = device_manager.get_devices_dir_path()
        assert devices_path == devices_dir
