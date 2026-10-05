"""Spatial-block and matched-budget helpers for the catalogue pseudo-holdout."""

from __future__ import annotations

import numpy as np


def spatial_quadrant_region_masks(shape: tuple[int, int]) -> dict[str, np.ndarray]:
    """Return the four full, non-overlapping regions used as spatial folds."""
    height, width = map(int, shape)
    if height < 2 or width < 2:
        raise ValueError("raster must be at least 2 by 2")
    mid_row, mid_col = height // 2, width // 2
    extents = {
        "NW": (0, mid_row, 0, mid_col),
        "NE": (0, mid_row, mid_col, width),
        "SW": (mid_row, height, 0, mid_col),
        "SE": (mid_row, height, mid_col, width),
    }
    masks: dict[str, np.ndarray] = {}
    for name, (r0, r1, c0, c1) in extents.items():
        mask = np.zeros((height, width), dtype=bool)
        mask[r0:r1, c0:c1] = True
        masks[name] = mask
    return masks


def spatial_quadrant_masks(shape: tuple[int, int], *, guard_px: int = 3) -> dict[str, np.ndarray]:
    """Return four disjoint inner quadrants with a guard around block boundaries.

    ``guard_px=3`` corresponds to 300 m for the competition's 100 m grid. Outer
    raster edges are guarded too. The masks deliberately omit the boundary strip
    so a nearby fault outside a test block cannot influence its score by the
    metric's 300 m kernel.
    """
    height, width = map(int, shape)
    if guard_px < 0:
        raise ValueError("guard_px must be non-negative")
    if height < 2 * guard_px + 2 or width < 2 * guard_px + 2:
        raise ValueError("raster is too small for the requested guard")
    mid_row, mid_col = height // 2, width // 2
    extents = {
        "NW": (guard_px, mid_row - guard_px, guard_px, mid_col - guard_px),
        "NE": (guard_px, mid_row - guard_px, mid_col + guard_px, width - guard_px),
        "SW": (mid_row + guard_px, height - guard_px, guard_px, mid_col - guard_px),
        "SE": (mid_row + guard_px, height - guard_px, mid_col + guard_px, width - guard_px),
    }
    masks: dict[str, np.ndarray] = {}
    for name, (r0, r1, c0, c1) in extents.items():
        if r1 <= r0 or c1 <= c0:
            raise ValueError(f"quadrant {name} is empty after applying guard")
        mask = np.zeros((height, width), dtype=bool)
        mask[r0:r1, c0:c1] = True
        masks[name] = mask
    return masks


def top_budget_binary(
    score: np.ndarray,
    valid_mask: np.ndarray,
    *,
    budget: int,
) -> np.ndarray:
    """Select exactly ``budget`` highest positive scores; tie-break by flat index."""
    values = np.asarray(score, dtype=np.float32)
    valid = np.asarray(valid_mask, dtype=bool)
    if values.ndim != 2 or values.shape != valid.shape:
        raise ValueError("score and valid_mask must be matching 2-D arrays")
    if not np.all(np.isfinite(values[valid])):
        raise ValueError("score contains non-finite values inside valid mask")
    if np.any(values[valid] < 0):
        raise ValueError("score must be non-negative")
    if budget < 1:
        raise ValueError("budget must be positive")
    flat = values.ravel()
    eligible = np.flatnonzero(valid.ravel() & np.isfinite(flat) & (flat > 0.0))
    if eligible.size < budget:
        raise ValueError(
            f"only {eligible.size:,} positive-scored cells are available, below requested budget {budget:,}"
        )
    # lexsort uses the last key as primary: descending score, then flat row-major index.
    order = np.lexsort((eligible, -flat[eligible]))
    chosen = eligible[order[:budget]]
    output = np.zeros(values.shape, dtype=bool)
    output.ravel()[chosen] = True
    return output
