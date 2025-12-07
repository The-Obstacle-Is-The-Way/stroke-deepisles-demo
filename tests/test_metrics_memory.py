from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from stroke_deepisles_demo.metrics import load_nifti_as_array


def test_load_nifti_uses_float32() -> None:
    """Test that load_nifti_as_array returns float32 data."""

    with patch("stroke_deepisles_demo.metrics.nib.load") as mock_load:
        mock_img = MagicMock()
        mock_load.return_value = mock_img

        # Setup mock data (simulating return value of get_fdata)
        # Since we expect the code to ask for float32, we make the mock return float32
        mock_data = np.zeros((10, 10, 10), dtype=np.float32)
        mock_img.get_fdata.return_value = mock_data

        mock_img.header.get_zooms.return_value = (1.0, 1.0, 1.0)

        # Call function
        data, _ = load_nifti_as_array(Path("test.nii.gz"))

        # Verify result dtype
        assert data.dtype == np.float32

        # Verify get_fdata was called with dtype argument
        mock_img.get_fdata.assert_called_with(dtype=np.float32)
