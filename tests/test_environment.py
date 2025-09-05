"""Test to verify the testing environment is properly set up."""


def test_environment_setup():
    """Test that basic Python functionality works."""
    assert 1 + 1 == 2


def test_imports():
    """Test that required dependencies can be imported."""
    import pytest
    import pydantic
    import pandas
    import filelock

    assert pytest is not None
    assert pydantic is not None
    assert pandas is not None
    assert filelock is not None


def test_project_structure():
    """Test that project structure exists."""
    import os
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    # Check main source directories exist
    assert (project_root / "src" / "ynab_io").exists()
    assert (project_root / "src" / "categorization").exists()
    assert (project_root / "src" / "simulation").exists()
    assert (project_root / "src" / "orchestration").exists()

    # Check key files exist
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "CLAUDE.md").exists()
    assert (project_root / "TASKS.md").exists()
