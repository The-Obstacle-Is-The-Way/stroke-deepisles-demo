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
    nifti_to_gradio_url,
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


class TestNiftiToGradioUrl:
    """Tests for nifti_to_gradio_url (Issue #19 optimization)."""

    def test_returns_gradio_api_format(self, synthetic_nifti_3d: Path) -> None:
        """Returns URL in Gradio API format."""
        url = nifti_to_gradio_url(synthetic_nifti_3d)

        assert url.startswith("/gradio_api/file=")

    def test_uses_absolute_path(self, synthetic_nifti_3d: Path) -> None:
        """URL contains absolute path to file."""
        url = nifti_to_gradio_url(synthetic_nifti_3d)

        # Extract path from URL
        path_part = url.replace("/gradio_api/file=", "")
        assert path_part.startswith("/")  # Absolute path
        assert "synthetic.nii.gz" in path_part

    def test_preserves_file_extension(self, synthetic_nifti_3d: Path) -> None:
        """URL preserves .nii.gz extension."""
        url = nifti_to_gradio_url(synthetic_nifti_3d)

        assert url.endswith(".nii.gz")

    def test_no_base64_encoding(self, synthetic_nifti_3d: Path) -> None:
        """URL does not contain base64-encoded data (Issue #19 requirement)."""
        url = nifti_to_gradio_url(synthetic_nifti_3d)

        # Base64 data URLs start with "data:" and contain ";base64,"
        assert not url.startswith("data:")
        assert ";base64," not in url


class TestRenderSliceComparisonProbabilityMask:
    """Tests for render_slice_comparison with probability masks (Issue #23).

    This test class verifies that probability-valued prediction masks
    are rendered visibly. The bug occurs when:
    - Ground truth is binary (0 or 1) → renders as visible green
    - Prediction is probability (0.1-0.5) → renders as nearly-invisible white

    See: docs/specs/23-slice-comparison-overlay-bug.md
    """

    def test_probability_mask_has_visible_overlay(
        self,
        synthetic_nifti_3d: Path,
        synthetic_probability_mask: Path,
    ) -> None:
        """
        Probability mask should produce visible overlay in rendering.

        This test exposes the bug where low probability values (e.g., 0.3)
        render as nearly-white in the "Reds" colormap and are invisible.
        """
        fig = render_slice_comparison(
            synthetic_nifti_3d,
            synthetic_probability_mask,  # Probability values 0.3, 0.7
            ground_truth_path=None,
        )

        # Get the prediction axis (index 1)
        ax = fig.axes[1]

        # The axis should have at least 2 images (DWI background + overlay)
        images = ax.get_images()
        assert len(images) >= 2, "Prediction panel should have overlay image"

        # The overlay should have non-zero alpha (visible)
        overlay = images[1]
        alpha = overlay.get_alpha()
        assert alpha is None or alpha > 0  # None means default alpha (1.0)

        plt.close(fig)

    def test_binary_vs_probability_mask_comparison(
        self,
        synthetic_nifti_3d: Path,
        synthetic_binary_mask: Path,
        synthetic_probability_mask: Path,
    ) -> None:
        """
        Both binary and probability masks should render visible overlays.

        This is the core test for Issue #23. If the probability mask renders
        invisibly while the binary mask renders visibly, the bug is confirmed.
        """
        # Render with binary mask (expected to work)
        fig_binary = render_slice_comparison(
            synthetic_nifti_3d,
            synthetic_binary_mask,
            ground_truth_path=None,
        )

        # Render with probability mask (may be invisible - the bug)
        fig_prob = render_slice_comparison(
            synthetic_nifti_3d,
            synthetic_probability_mask,
            ground_truth_path=None,
        )

        # Get overlay data from both
        binary_overlay = fig_binary.axes[1].get_images()[1].get_array()
        prob_overlay = fig_prob.axes[1].get_images()[1].get_array()

        # Both should have non-masked (visible) pixels
        binary_visible = (
            not binary_overlay.mask.all()  # type: ignore[union-attr]
            if hasattr(binary_overlay, "mask")
            else True
        )
        prob_visible = (
            not prob_overlay.mask.all()  # type: ignore[union-attr]
            if hasattr(prob_overlay, "mask")
            else True
        )

        assert binary_visible, "Binary mask overlay should have visible pixels"
        assert prob_visible, "Probability mask overlay should have visible pixels"

        plt.close(fig_binary)
        plt.close(fig_prob)


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
