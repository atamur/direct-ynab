"""Tests for DeviceManager composite knowledge string parsing."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from ynab_io.device_manager import DeviceManager


class TestDeviceManagerCompositeKnowledge:
    """Test composite knowledge string parsing functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.device_manager = DeviceManager()

    def test_parse_version_string_single_version(self):
        """Test parsing single version strings (existing functionality)."""
        device_id, version_num = self.device_manager.parse_version_string("A-86")
        assert device_id == "A"
        assert version_num == 86

        device_id, version_num = self.device_manager.parse_version_string("B-123")
        assert device_id == "B"
        assert version_num == 123

    def test_parse_version_string_invalid_format(self):
        """Test that invalid version strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid version format"):
            self.device_manager.parse_version_string("invalid")
        
        with pytest.raises(ValueError, match="Invalid version format"):
            self.device_manager.parse_version_string("A-")
        
        with pytest.raises(ValueError, match="Invalid version format"):
            self.device_manager.parse_version_string("-86")

    def test_parse_composite_knowledge_string_simple(self):
        """Test parsing composite knowledge strings like 'A-11429,B-63'."""
        composite_knowledge = "A-11429,B-63"
        
        # Should now work with our implementation
        latest_version = self.device_manager.get_latest_version([composite_knowledge])
        assert latest_version == "A-11429"  # A-11429 is higher than B-63

    def test_parse_composite_knowledge_string_complex(self):
        """Test parsing complex composite knowledge strings."""
        composite_knowledge = "A-11429,B-63,C-52,E-232,F-31"
        
        # Should now work with our implementation
        latest_version = self.device_manager.get_latest_version([composite_knowledge])
        assert latest_version == "A-11429"  # A-11429 is the highest version

    def test_get_latest_version_with_composite_knowledge(self):
        """Test get_latest_version with mixed single and composite knowledge strings."""
        versions = [
            "A-86",  # Single version
            "A-11429,B-63,C-52,E-232,F-31",  # Composite version
            "B-100"  # Single version
        ]
        
        # Should now work and return the highest version across all strings
        latest_version = self.device_manager.get_latest_version(versions)
        assert latest_version == "A-11429"  # A-11429 is the highest version across all strings

    def test_find_device_with_latest_knowledge_composite(self):
        """Test finding device with latest knowledge when composite strings are present."""
        device_knowledges = {
            "device-guid-1": "A-86",
            "device-guid-2": "A-11429,B-63,C-52,E-232,F-31",  # This has the latest version
            "device-guid-3": "B-100"
        }
        
        # Should now work and return the device with the highest knowledge version
        result = self.device_manager._find_device_with_latest_knowledge(device_knowledges)
        assert result == "device-guid-2"  # device-guid-2 has A-11429 which is the highest

    def test_get_global_knowledge_with_composite_strings(self):
        """Test get_global_knowledge when .ydevice files contain composite knowledge strings."""
        # Mock the directory structure and file contents
        mock_devices_dir = Mock()
        mock_ydevice_files = [
            Mock(name="A.ydevice"),
            Mock(name="B.ydevice")
        ]
        
        # Mock file contents with composite knowledge
        mock_file_contents = [
            {"knowledge": "A-86"},
            {"knowledge": "A-11429,B-63,C-52,E-232,F-31"}  # Composite knowledge
        ]
        
        with patch.object(self.device_manager, '_get_devices_dir', return_value=mock_devices_dir), \
             patch.object(mock_devices_dir, 'glob', return_value=mock_ydevice_files), \
             patch('builtins.open') as mock_open, \
             patch('json.load') as mock_json_load:
            
            mock_json_load.side_effect = mock_file_contents
            
            # Should now work and return the highest version from all knowledge strings
            result = self.device_manager.get_global_knowledge()
            assert result == "A-11429"  # A-11429 is the highest version across all knowledge strings

    def test_update_device_knowledge_with_composite_string(self):
        """Test that update_device_knowledge validates composite knowledge strings."""
        mock_ydevice_path = Path("/mock/path/A.ydevice")
        composite_knowledge = "A-11429,B-63,C-52,E-232,F-31"
        
        # create_ydevice_structure calls parse_version_string for validation
        with pytest.raises(ValueError, match="Invalid version format"):
            self.device_manager.create_ydevice_structure(
                device_guid="test-guid",
                short_id="A",
                friendly_name="Test Device",
                knowledge=composite_knowledge
            )


class TestDeviceManagerCompositeKnowledgeHelpers:
    """Test helper methods for composite knowledge parsing."""

    def setup_method(self):
        """Set up test environment."""
        self.device_manager = DeviceManager()

    def test_parse_composite_knowledge_string_method(self):
        """Test the parse_composite_knowledge_string method."""
        # Test single version string
        result = self.device_manager.parse_composite_knowledge_string("A-86")
        assert result == [("A", 86)]
        
        # Test composite version string
        result = self.device_manager.parse_composite_knowledge_string("A-11429,B-63")
        assert result == [("A", 11429), ("B", 63)]
        
        # Test complex composite version string
        result = self.device_manager.parse_composite_knowledge_string("A-11429,B-63,C-52,E-232,F-31")
        expected = [("A", 11429), ("B", 63), ("C", 52), ("E", 232), ("F", 31)]
        assert result == expected

    def test_get_latest_version_from_composite_method(self):
        """Test getting latest version from composite knowledge string."""
        # Test single version string
        result = self.device_manager.get_latest_version_from_composite("A-86")
        assert result == "A-86"
        
        # Test composite version string - should return highest version
        result = self.device_manager.get_latest_version_from_composite("A-11429,B-63")
        assert result == "A-11429"
        
        # Test complex composite version string
        composite_knowledge = "A-11429,B-63,C-52,E-232,F-31"
        result = self.device_manager.get_latest_version_from_composite(composite_knowledge)
        assert result == "A-11429"  # A-11429 is the highest version
        
        # Test where different device has higher version
        result = self.device_manager.get_latest_version_from_composite("A-100,B-15000")
        assert result == "B-15000"  # B-15000 is higher than A-100

    def test_parse_composite_knowledge_string_error_handling(self):
        """Test error handling in composite knowledge string parsing."""
        # Test empty string
        with pytest.raises(ValueError, match="Knowledge string cannot be empty"):
            self.device_manager.parse_composite_knowledge_string("")
        
        # Test non-string input
        with pytest.raises(ValueError, match="Knowledge string must be a string"):
            self.device_manager.parse_composite_knowledge_string(123)
        
        # Test composite string with invalid part
        with pytest.raises(ValueError, match="Invalid version part 'invalid'"):
            self.device_manager.parse_composite_knowledge_string("A-86,invalid,B-100")

    def test_get_latest_version_error_handling(self):
        """Test error handling in get_latest_version method."""
        # Test with invalid version string in list
        with pytest.raises(ValueError, match="Invalid version string"):
            self.device_manager.get_latest_version(["A-86", "invalid", "B-100"])