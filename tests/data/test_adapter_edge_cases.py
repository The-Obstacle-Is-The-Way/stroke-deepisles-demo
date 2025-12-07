from pathlib import Path

import pytest

from stroke_deepisles_demo.data.adapter import build_local_dataset


def test_build_local_dataset_raises_on_missing_dir() -> None:
    """Test that build_local_dataset raises FileNotFoundError for non-existent directory."""
    missing_dir = Path("/non/existent/path/to/data")

    with pytest.raises(FileNotFoundError, match="Data directory not found"):
        build_local_dataset(missing_dir)
