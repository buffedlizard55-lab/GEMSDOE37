"""Fail-closed checks on every published deliverable and its receipts.

These tests pin the bytes that the site points at, so a stale
``docs/data/current_submission.json`` (or a half-written TIFF) cannot silently ship.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RECORD = json.loads((DOCS / "data" / "current_submission.json").read_text())

FILENAME = RECORD["filename"]
TIF = DOCS / "downloads" / FILENAME
ZIP = TIF.with_suffix(".zip")
EXPECTED_SHA256 = RECORD["sha256"]


def test_pointer_is_submission_ready_and_files_exist():
    assert RECORD["status"] == "CALIBRATION_GATE_PASSED_UNSCORED"
    assert TIF.exists(), f"{TIF} is missing"
    assert ZIP.exists(), f"{ZIP} is missing"
    for key in ("verification_path", "forecast_path", "checks_path", "holdout_report_path"):
        path = DOCS / RECORD[key]
        assert path.exists(), f"{key} points at missing file {path}"


def test_csp_sha256_matches_receipts():
    digest = hashlib.sha256(TIF.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA256
    checks = json.loads((DOCS / RECORD["checks_path"]).read_text())
    verification = json.loads((DOCS / RECORD["verification_path"]).read_text())
    assert checks["sha256"] == digest
    assert verification["sha256"] == digest


def test_csp_geotiff_contract():
    with rasterio.open(TIF) as src:
        assert src.driver == "GTiff"
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.crs is not None and src.crs.to_epsg() == 32611
        assert src.shape == (3730, 3292)
        assert src.nodata is None
        values = src.read(1)
    assert np.all(np.isfinite(values))
    assert float(values.min()) >= 0.0 and float(values.max()) <= 1.0
    assert int((values > 0.0).sum()) == int(RECORD["positive_pixels"])
    assert set(np.unique(values)).issubset({0.0, 1.0})


def test_csp_zip_contains_the_same_bytes():
    with zipfile.ZipFile(ZIP) as archive:
        assert len(archive.infolist()) == 1
        name = archive.infolist()[0].filename
        assert name == FILENAME
        assert hashlib.sha256(archive.read(name)).hexdigest() == EXPECTED_SHA256


def test_csp_uniqueness_and_note_are_honest():
    assert RECORD["uniqueness"]["is_copy_or_relabel"] is False
    assert RECORD["uniqueness"]["max_jaccard_vs_prior_submissions"] < 0.10
    assert RECORD["organizer_score"] is None
    note = RECORD["submission_note"]
    assert 0 < len(note) <= 200
    assert "unscored" in note.lower()
    assert "no organizer score" in RECORD["warning"].lower()


CSP_FILENAME = "gemsdoe37-csp-concealed-persistence-20261005T060000Z-8ba2edb16e5c.tif"
CSP_TIF = DOCS / "downloads" / CSP_FILENAME


def test_alternative_csp_artifact_is_still_present_and_valid():
    """The superseded CSP candidate is kept, not deleted, and must stay valid."""
    assert CSP_TIF.exists()
    with rasterio.open(CSP_TIF) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.crs.to_epsg() == 32611
        assert src.shape == (3730, 3292)
        values = src.read(1)
    assert np.all(np.isfinite(values))
    assert float(values.min()) >= 0.0 and float(values.max()) <= 1.0
    assert int((values > 0.0).sum()) == 37_000


def test_recommended_candidate_beats_the_alternative_geometry_on_the_same_holdout():
    """The recommendation is justified by a measurement, not by preference."""
    sweep = json.loads(
        (ROOT / "research/receipts/h6_sweep.json").read_text()
    )["pooled"]["b80000_s2.9_o3.0"]["pooled_dti"]
    csp = json.loads(
        (ROOT / "research/receipts/h6_sweep_csp_geometry.json").read_text()
    )["pooled"]["b37000_s3.0_o6.0"]["pooled_dti"]
    assert sweep > csp
    assert RECORD["positive_pixels"] == 80_000
