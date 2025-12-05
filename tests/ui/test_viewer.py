"""Tests for viewer module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib

# Non-interactive backend for tests - must be before pyplot import
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from stroke_deepisles_demo.ui.viewer import (
    create_niivue_html,
    get_slice_at_max_lesion,
    render_3panel_view,
    render_slice_comparison,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestRender3PanelView:
    """Tests for render_3panel_view."""

    def test_returns_matplotlib_figure(self, synthetic_nifti_3d: Path) -> None:
        """Returns a matplotlib Figure object."""
        fig = render_3panel_view(synthetic_nifti_3d)

        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_has_three_axes(self, synthetic_nifti_3d: Path) -> None:
        """Figure has 3 subplots (axial, coronal, sagittal)."""
        fig = render_3panel_view(synthetic_nifti_3d)

        assert len(fig.axes) == 3
        plt.close(fig)

    def test_overlay_mask_when_provided(self, synthetic_nifti_3d: Path, temp_dir: Path) -> None:
        """Overlays mask when mask_path provided."""
        # Create a simple mask
        import nibabel as nib

        mask_data = np.zeros((10, 10, 10), dtype=np.uint8)
        mask_data[4:6, 4:6, 4:6] = 1
        mask_img = nib.Nifti1Image(mask_data, np.eye(4))  # type: ignore
        mask_path = temp_dir / "mask.nii.gz"
        nib.save(mask_img, mask_path)  # type: ignore

        fig = render_3panel_view(synthetic_nifti_3d, mask_path=mask_path)

        # Should not raise
        assert fig is not None
        plt.close(fig)


class TestRenderSliceComparison:
    """Tests for render_slice_comparison."""

    def test_comparison_without_ground_truth(self, synthetic_nifti_3d: Path) -> None:
        """Works when ground truth is None."""
        fig = render_slice_comparison(
            synthetic_nifti_3d,
            synthetic_nifti_3d,  # Use same as prediction for test
            ground_truth_path=None,
        )

        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_comparison_with_ground_truth(self, synthetic_nifti_3d: Path) -> None:
        """Works when ground truth is provided."""
        fig = render_slice_comparison(
            synthetic_nifti_3d,
            synthetic_nifti_3d,
            ground_truth_path=synthetic_nifti_3d,
        )

        assert isinstance(fig, Figure)
        plt.close(fig)


class TestGetSliceAtMaxLesion:
    """Tests for get_slice_at_max_lesion."""

    def test_finds_slice_with_lesion(self, temp_dir: Path) -> None:
        """Returns slice index where lesion is largest."""
        import nibabel as nib

        # Create mask with lesion at slice 7
        mask_data = np.zeros((10, 10, 10), dtype=np.uint8)
        mask_data[:, :, 7] = 1  # Full slice 7 is lesion

        mask_img = nib.Nifti1Image(mask_data, np.eye(4))  # type: ignore
        mask_path = temp_dir / "mask.nii.gz"
        nib.save(mask_img, mask_path)  # type: ignore

        slice_idx = get_slice_at_max_lesion(mask_path, orientation="axial")

        assert slice_idx == 7

    def test_returns_middle_for_empty_mask(self, temp_dir: Path) -> None:
        """Returns middle slice when mask is empty."""
        import nibabel as nib

        mask_data = np.zeros((10, 10, 20), dtype=np.uint8)
        mask_img = nib.Nifti1Image(mask_data, np.eye(4))  # type: ignore
        mask_path = temp_dir / "mask.nii.gz"
        nib.save(mask_img, mask_path)  # type: ignore

        slice_idx = get_slice_at_max_lesion(mask_path, orientation="axial")

        assert slice_idx == 10  # Middle of 20


class TestCreateNiivueHtml:
    """Tests for create_niivue_html."""

    def test_includes_volume_url(self) -> None:
        """Generated HTML includes the volume URL."""
        html = create_niivue_html("http://example.com/brain.nii.gz")

        assert "http://example.com/brain.nii.gz" in html

    def test_includes_mask_when_provided(self) -> None:
        """Generated HTML includes mask URL when provided."""
        html = create_niivue_html(
            "http://example.com/brain.nii.gz",
            mask_url="http://example.com/mask.nii.gz",
        )

        assert "http://example.com/mask.nii.gz" in html

    def test_sets_height(self) -> None:
        """Generated HTML respects height parameter."""
        html = create_niivue_html(
            "http://example.com/brain.nii.gz",
            height=600,
        )

        assert "height:600px" in html
