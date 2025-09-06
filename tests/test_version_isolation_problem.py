"""Test demonstrating the version isolation problem.

This test shows that the current version_aware_parser fixture doesn't properly
isolate tests from newer deltas - it parses ALL deltas first, then restores,
which can cause issues with unsupported data types from newer deltas.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from ynab_io.parser import YnabParser


class TestVersionIsolationProblem:
    """Test cases demonstrating the version isolation problem."""

    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")

    def test_version_isolation_problem_with_parsing_order(self, test_budget_path):
        """Test that demonstrates the old problematic behavior: parse all then restore.

        This test shows the core problem with the OLD approach: when applying all deltas
        then restoring, newer deltas get processed that might contain unsupported data.
        """
        # Mock to track which deltas are parsed
        with patch.object(YnabParser, "_apply_delta") as mock_apply_delta:
            parser = YnabParser(test_budget_path)

            # Simulate the OLD problematic fixture behavior: parse() then restore_to_version()
            parser.parse()  # This applies ALL deltas
            parser.restore_to_version(67)  # Then restores to version 67

            # The problem: _apply_delta was called for many deltas, including those beyond version 67
            # Get all available delta files
            parser._discover_delta_files()

            # Check that we processed deltas beyond version 67 (the problem)
            versions_processed = []
            for call_args in mock_apply_delta.call_args_list:
                delta_file = call_args[0][0]  # First argument to _apply_delta
                end_version = parser._get_version_end_number(delta_file)
                versions_processed.append(end_version)

            # This is the problem: we processed deltas beyond version 67
            deltas_beyond_target = [v for v in versions_processed if v > 67]
            assert len(deltas_beyond_target) > 0, "Expected to find deltas beyond version 67 were processed"

    def test_desired_behavior_parse_only_up_to_version(self, test_budget_path):
        """Test showing the desired behavior: only parse deltas up to target version.

        This test verifies that parse_up_to_version method exists and works.
        """
        parser = YnabParser(test_budget_path)

        # This method should now exist and work
        budget = parser.parse_up_to_version(67)
        assert budget is not None
        assert hasattr(parser, "applied_deltas")

        # Verify that only deltas up to version 67 were applied
        for delta_file in parser.applied_deltas:
            end_version = parser._get_version_end_number(delta_file)
            assert end_version <= 67, f"Delta {delta_file.name} has end version {end_version} > target 67"

    def test_old_behavior_vs_new_fixture_behavior(self, test_budget_path):
        """Test comparing old problematic behavior vs new fixed fixture behavior."""
        target_version = 67

        # Test OLD behavior: parse all deltas then restore (problematic)
        with patch.object(YnabParser, "_apply_delta") as mock_apply_delta_old:
            parser_old = YnabParser(test_budget_path)

            # Get all delta files to know which ones should NOT be parsed
            delta_files = parser_old._discover_delta_files()
            deltas_beyond_target = []

            for delta_file in delta_files:
                end_version = parser_old._get_version_end_number(delta_file)
                if end_version > target_version:
                    deltas_beyond_target.append(delta_file)

            # Simulate OLD problematic fixture behavior
            parser_old.parse()  # This applies ALL deltas
            parser_old.restore_to_version(target_version)  # Then restores

            # OLD behavior processed deltas beyond target version (the problem)
            assert len(deltas_beyond_target) > 0, "Test setup issue: no deltas beyond target version found"

            deltas_beyond_target_were_processed = []
            for delta_file in deltas_beyond_target:
                delta_was_processed = any(
                    call_args[0][0] == delta_file for call_args in mock_apply_delta_old.call_args_list
                )
                if delta_was_processed:
                    deltas_beyond_target_were_processed.append(delta_file)

            # OLD behavior: problematic deltas were processed
            assert (
                len(deltas_beyond_target_were_processed) > 0
            ), "Old behavior should have processed deltas beyond target"

        # Test NEW behavior: parse_up_to_version (fixed)
        with patch.object(YnabParser, "_apply_delta") as mock_apply_delta_new:
            parser_new = YnabParser(test_budget_path)
            parser_new.parse_up_to_version(target_version)

            # NEW behavior should NOT process deltas beyond target version
            deltas_beyond_target_were_processed_new = []
            for delta_file in deltas_beyond_target:
                delta_was_processed = any(
                    call_args[0][0] == delta_file for call_args in mock_apply_delta_new.call_args_list
                )
                if delta_was_processed:
                    deltas_beyond_target_were_processed_new.append(delta_file)

            # NEW behavior: no problematic deltas were processed (fixed!)
            assert (
                len(deltas_beyond_target_were_processed_new) == 0
            ), "New behavior should not process deltas beyond target"
