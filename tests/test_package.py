"""Smoke tests for package structure."""

from __future__ import annotations


def test_package_imports() -> None:
    """Verify the package can be imported."""
    import stroke_deepisles_demo

    assert stroke_deepisles_demo.__version__ == "0.1.0"


def test_core_modules_import() -> None:
    """Verify core modules can be imported without side effects."""
    from stroke_deepisles_demo.core import config, exceptions, types

    assert config.settings is not None
    assert types.CaseFiles is not None
    assert exceptions.StrokeDemoError is not None


def test_subpackages_exist() -> None:
    """Verify subpackage structure exists."""
    from stroke_deepisles_demo import data, inference, ui

    # These are stubs, just verify they exist
    assert data is not None
    assert inference is not None
    assert ui is not None
