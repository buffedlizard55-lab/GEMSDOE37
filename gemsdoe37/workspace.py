"""Helpers for reading the on-disk H6 feature workspace."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def load_meta(work: str | Path) -> dict:
    return json.loads((Path(work) / "meta.json").read_text(encoding="utf-8"))


def load_columns(
    work: str | Path, indices: list[int], rows: np.ndarray | None = None
) -> np.ndarray:
    """Load selected feature columns for selected rows into one float32 matrix.

    Columns live in one ``.npy`` file each so that an arbitrary subset of rows
    and columns can be materialised without ever holding the full stack.
    """
    work = Path(work)
    if rows is None:
        rows = np.arange(np.load(work / "valid_index.npy").size)
    out = np.empty((rows.size, len(indices)), dtype=np.float32)
    for position, index in enumerate(indices):
        column = np.load(work / "feat" / f"{index:03d}.npy", mmap_mode="r")
        out[:, position] = column[rows]
    return out
