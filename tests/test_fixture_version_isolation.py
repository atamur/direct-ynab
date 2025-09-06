"""Test that the version_aware_parser fixture provides true version isolation."""

from pathlib import Path

import pytest

from ynab_io.testing import budget_version


class TestFixtureVersionIsolation:
    """Test that the fixture correctly isolates versions."""

    @pytest.fixture
    def test_budget_path(self):
        """Path to the test budget fixture."""
        return Path("tests/fixtures/My Test Budget~E0C1460F.ynab4")

    @budget_version(67)
    def test_fixture_only_applies_deltas_up_to_target_version(self, version_aware_parser):
        """Test that version_aware_parser fixture only applies deltas up to the target version."""
        parser = version_aware_parser

        # Verify that only deltas up to version 67 were applied
        for delta_file in parser.applied_deltas:
            end_version = parser._get_version_end_number(delta_file)
            assert end_version <= 67, f"Delta {delta_file.name} has end version {end_version} > 67"

        # Should have exactly 1 delta applied (the one that ends at version 67)
        assert len(parser.applied_deltas) == 1
        assert parser.applied_deltas[0].name == "A-63_A-67.ydiff"

    def test_fixture_without_version_annotation_applies_all_deltas(self, version_aware_parser):
        """Test that fixture without version annotation applies all deltas."""
        parser = version_aware_parser

        # Should have applied all available deltas
        all_delta_files = parser._discover_delta_files()
        assert len(parser.applied_deltas) == len(all_delta_files)

    @budget_version(0)
    def test_fixture_with_version_zero_applies_no_deltas(self, version_aware_parser):
        """Test that version 0 applies no deltas (base state only)."""
        parser = version_aware_parser

        # Should have no deltas applied for version 0
        assert len(parser.applied_deltas) == 0
