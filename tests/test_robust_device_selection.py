"""Specific tests for robust device selection in multi-device scenarios."""

import json

from ynab_io.parser import YnabParser


class TestRobustDeviceSelection:
    """Tests for robust device selection based on knowledge versions."""

    def test_parser_chooses_device_with_latest_knowledge_when_alphabetically_later(self, tmp_path):
        """Test that parser chooses device with latest knowledge even when it's alphabetically later."""
        # This test will definitely fail with current implementation
        # which just picks the first device alphabetically
        budget_dir = tmp_path / "priority_test_budget"
        budget_dir.mkdir()
        data_dir = budget_dir / "data1~PRIORITY"
        data_dir.mkdir()
        devices_dir = data_dir / "devices"
        devices_dir.mkdir()

        # Create device A with older knowledge (A-10) - alphabetically first
        device_a_guid = "DEVICE-A-OLD"
        device_a_dir = data_dir / device_a_guid
        device_a_dir.mkdir()
        ydevice_a = devices_dir / "A.ydevice"
        with open(ydevice_a, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_a_guid,
                    "shortDeviceId": "A",
                    "friendlyName": "Device A Old",
                    "knowledge": "A-10",  # Very old knowledge
                    "knowledgeInFullBudgetFile": "A-10",
                },
                f,
            )

        # Create Budget.yfull in device A (should NOT be used)
        budget_yfull_a = device_a_dir / "Budget.yfull"
        with open(budget_yfull_a, "w") as f:
            json.dump(
                {
                    "accounts": [
                        {
                            "entityId": "old-account",
                            "accountName": "Old Account",
                            "accountType": "Checking",
                            "onBudget": True,
                            "sortableIndex": 0,
                            "hidden": False,
                            "entityVersion": "A-10",
                        }
                    ],
                    "payees": [],
                    "transactions": [],
                },
                f,
            )

        # Create device C with MUCH newer knowledge (C-200) - alphabetically later
        device_c_guid = "DEVICE-C-NEWEST"
        device_c_dir = data_dir / device_c_guid
        device_c_dir.mkdir()
        ydevice_c = devices_dir / "C.ydevice"
        with open(ydevice_c, "w") as f:
            json.dump(
                {
                    "deviceGUID": device_c_guid,
                    "shortDeviceId": "C",
                    "friendlyName": "Device C Newest",
                    "knowledge": "C-200",  # Much newer knowledge
                    "knowledgeInFullBudgetFile": "C-200",
                },
                f,
            )

        # Create Budget.yfull in device C (SHOULD be used)
        budget_yfull_c = device_c_dir / "Budget.yfull"
        with open(budget_yfull_c, "w") as f:
            json.dump(
                {
                    "accounts": [
                        {
                            "entityId": "new-account",
                            "accountName": "New Account",
                            "accountType": "Checking",
                            "onBudget": True,
                            "sortableIndex": 0,
                            "hidden": False,
                            "entityVersion": "C-200",
                        }
                    ],
                    "payees": [],
                    "transactions": [],
                },
                f,
            )

        # Initialize parser
        parser = YnabParser(budget_dir)

        # Current implementation will select device A (first alphabetically)
        # But we want device C (latest knowledge)

        # If current implementation is used, this should fail
        assert parser.device_dir.name == device_c_guid, (
            f"Expected device C ({device_c_guid}) but got {parser.device_dir.name}"
        )
