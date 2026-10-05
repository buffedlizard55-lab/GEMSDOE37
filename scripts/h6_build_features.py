#!/usr/bin/env python
"""Build the H6 feature stack as an on-disk float32 memmap.

Inputs (hash-pinned, see research/sources.md):
  data/raw/training_features.tif   19-band GeoDAWN/INGENIOUS numeric stack
  data/raw/labels.tif              known USGS/INGENIOUS faults (1), valid (0), outside (-1)
  data/raw/sample_submission.tif   grid template

Output:
  <work>/feat/NNN.npy   one float32 column per feature (length = valid pixels)
  <work>/meta.json      feature names, shape, footprint index
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio

from gemsdoe37.discovery import (
    gradient_magnitude,
    rank_normalize,
    ridge_strength,
    scales_survived,
)
from gemsdoe37.persistence import h0_prominence

SCALES = (1.0, 2.0, 4.0, 8.0)

# Bands chosen for scale-space treatment, one per independent physics family.
STRUCTURAL_BANDS = {
    "det_elev": 12,
    "tmi": 14,
    "rtp": 2,
    "iso_grav_anom": 13,
    "cond_surf": 17,
    "depth_to_base_surf": 15,
    "geod_2ndinv": 4,
}

FAMILIES = {
    "topo": ["det_elev"],
    "mag": ["tmi", "rtp"],
    "grav": ["iso_grav_anom"],
    "elec": ["cond_surf", "depth_to_base_surf"],
    "strain": ["geod_2ndinv"],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="data/raw")
    parser.add_argument("--work", default="data/work")
    args = parser.parse_args()
    raw = Path(args.raw)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    with rasterio.open(raw / "sample_submission.tif") as template:
        footprint = np.isfinite(template.read(1))
        shape = footprint.shape
    with rasterio.open(raw / "labels.tif") as src:
        labels = src.read(1)
    known = labels == 1
    assert np.array_equal(labels == -1, ~footprint), "label -1 must be exactly outside the footprint"

    with rasterio.open(raw / "training_features.tif") as src:
        band_names = [d.split(" - ")[0] for d in src.descriptions]
        nodata = src.nodata
        raw_bands = {}
        for index in range(1, src.count + 1):
            array = src.read(index).astype(np.float32)
            if nodata is not None:
                array[array <= -1e38] = np.nan
            array[~footprint] = np.nan
            raw_bands[band_names[index - 1]] = array

    for name, index in STRUCTURAL_BANDS.items():
        assert band_names[index - 1] == name, f"band {index} is {band_names[index - 1]}, expected {name}"

    valid_index = np.flatnonzero(footprint.ravel())
    n_valid = valid_index.size

    columns: list[str] = []
    feature_dir = work / "feat"
    feature_dir.mkdir(parents=True, exist_ok=True)

    def add(name: str, array: np.ndarray) -> None:
        """Rank-normalise one feature and stream it straight to disk.

        Features are stored one file per column so that peak memory stays near
        a single raster rather than the whole stack (this sandbox has 3 GB).
        """
        column = rank_normalize(np.nan_to_num(array, nan=0.0), footprint).ravel()[valid_index]
        np.save(feature_dir / f"{len(columns):03d}.npy", column.astype(np.float32))
        columns.append(name)
        print(f"  feature {len(columns):3d}  {name}", flush=True)

    # 1. raw bands, rank normalised
    for name in band_names:
        add(f"raw:{name}", raw_bands[name])

    # free the rasters that are not needed for the scale-space stage (3 GB box)
    for name in list(raw_bands):
        if name not in STRUCTURAL_BANDS:
            del raw_bands[name]

    # 2. scale-space structural responses + persistence certificates
    family_consensus: dict[str, np.ndarray] = {}
    for family, members in FAMILIES.items():
        ridge_stack: list[np.ndarray] = []
        for name in members:
            filled = np.nan_to_num(raw_bands[name], nan=float(np.nanmean(raw_bands[name])))
            for sigma in SCALES:
                grad = gradient_magnitude(filled, sigma)
                ridge = ridge_strength(filled, sigma)
                add(f"grad:{name}:s{sigma:g}", grad)
                add(f"ridge:{name}:s{sigma:g}", ridge)
                ridge_stack.append(rank_normalize(ridge, footprint))
        survived = scales_survived(ridge_stack, footprint, quantile=0.90)
        add(f"survived:{family}", survived)
        consensus = np.mean(ridge_stack, axis=0).astype(np.float32)
        consensus *= (survived / float(len(ridge_stack)))
        family_consensus[family] = consensus
        add(f"consensus:{family}", consensus)
        prominence = h0_prominence(consensus, footprint)
        add(f"persist:{family}", prominence)

    # 3. cross-family multi-physics corroboration
    stacked = np.stack([rank_normalize(v, footprint) for v in family_consensus.values()])
    add("xfam:mean", stacked.mean(axis=0))
    add("xfam:max", stacked.max(axis=0))
    add("xfam:second", np.sort(stacked, axis=0)[-2])
    add("xfam:count90", (stacked >= 0.90).sum(axis=0).astype(np.float32))

    meta = {
        "shape": list(shape),
        "n_valid": int(n_valid),
        "columns": columns,
        "scales_px": list(SCALES),
        "families": {k: v for k, v in FAMILIES.items()},
        "known_fault_pixels": int(known.sum()),
    }
    (work / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    np.save(work / "valid_index.npy", valid_index)
    np.save(work / "known.npy", known)
    np.save(work / "footprint.npy", footprint)
    print(f"wrote {n_valid} x {len(columns)} features to {feature_dir}")


if __name__ == "__main__":
    main()
