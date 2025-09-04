"""Integration test for the read-modify-write cycle."""

import json
from pathlib import Path
import shutil
from unittest.mock import patch

from ynab_io.parser import YnabParser
from ynab_io.writer import YnabWriter
from ynab_io.device_manager import DeviceManager
from ynab_io.models import Transaction

def test_read_modify_write_cycle(tmp_path):
    """Test the full read-modify-write cycle."""
    # Setup test environment
    budget_dir = tmp_path / "budget"
    shutil.copytree("/home/atamur/direct-ynab/tests/fixtures/My Test Budget~E0C1460F.ynab4", budget_dir)

    # 1. Load the budget
    parser = YnabParser(budget_dir)
    budget = parser.parse()

    # 2. Modify a transaction
    transaction_to_modify = budget.transactions[0]
    new_memo = "This is a test memo."
    transaction_to_modify.memo = new_memo
    
    # 3. Write the .ydiff
    device_manager = DeviceManager(budget_dir=budget_dir)
    writer = YnabWriter(device_manager=device_manager)
    
    global_knowledge = device_manager.get_global_knowledge()
    
    # Get the device guid for the current device
    ydevice_path = list((budget_dir / "data1~F5FF7453" / "devices").glob("*.ydevice"))[0]
    with open(ydevice_path, 'r') as f:
        device_data = json.load(f)
    device_guid = device_data["deviceGUID"]
    
    new_version = device_manager.increment_version(global_knowledge)
    transaction_to_modify.entityVersion = new_version

    with patch.object(writer, '_get_device_directory', return_value=budget_dir / "data1~F5FF7453" / device_guid):
        with patch.object(writer, '_get_ydevice_file_path', return_value=ydevice_path):
            result = writer.write_changes(
                entities={"transactions": [transaction_to_modify]},
                current_knowledge=global_knowledge
            )
    
    assert result["success"] is True

    # 4. Read the budget again
    parser2 = YnabParser(budget_dir)
    budget2 = parser2.parse()

    # 5. Verify the change
    modified_transaction = next(t for t in budget2.transactions if t.entityId == transaction_to_modify.entityId)
    assert modified_transaction.memo == new_memo
