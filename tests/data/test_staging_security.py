from pathlib import Path

import pytest

from stroke_deepisles_demo.core.exceptions import MissingInputError
from stroke_deepisles_demo.data.staging import _materialize_nifti


def test_materialize_nifti_rejects_url() -> None:
    """Test that _materialize_nifti rejects URLs (SSRF prevention)."""

    url = "http://example.com/malicious.nii.gz"
    dest = Path("/tmp/dest.nii.gz")

    # After fix, this should raise MissingInputError (treating it as a non-existent local file)
    # or a specific security error if we choose to implement one.
    # The recommendation was "Remove the HTTP code path entirely".
    # If removed, it falls through to "Assume local path string", checking if it exists.
    # Since "http://..." doesn't exist locally, it raises MissingInputError.

    with pytest.raises(MissingInputError, match="Source file does not exist"):
        _materialize_nifti(url, dest)
