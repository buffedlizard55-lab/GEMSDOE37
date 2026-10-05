import numpy as np
import pytest
import rasterio
from affine import Affine

from gemsdoe37.submission import validate_geotiff, write_submission_geotiff


def _write_template(path, *, width=8, height=6, epsg=32611, nodata=None):
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": f"EPSG:{epsg}",
        "transform": Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
        "nodata": nodata,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.zeros((height, width), dtype=np.float32), 1)


def test_submission_writer_matches_template_and_reopens(tmp_path):
    template = tmp_path / "template.tif"
    output = tmp_path / "unique-candidate.tif"
    _write_template(template)
    prediction = np.zeros((6, 8), dtype=np.float32)
    prediction[2, 3] = 1.0
    prediction[4, 5] = 0.5
    receipt = write_submission_geotiff(output, prediction, template, expected_budget=2)
    assert receipt["driver_is_gtiff"]
    assert receipt["single_band"]
    assert receipt["dtype_float32"]
    assert receipt["crs_matches_template"]
    assert receipt["nodata_tag_absent"]
    assert receipt["range_0_1_all_cells"]
    assert receipt["positive_pixels"] == 2
    with rasterio.open(output) as src:
        values = src.read(1)
        assert values[2, 3] == pytest.approx(1.0)
        assert values[4, 5] == pytest.approx(0.5)
        assert src.nodata is None


def test_writer_refuses_out_of_range_and_nan_before_creating_file(tmp_path):
    template = tmp_path / "template.tif"
    _write_template(template)
    output = tmp_path / "bad.tif"
    bad = np.zeros((6, 8), dtype=np.float32)
    bad[0, 0] = -3.4028235e38
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        write_submission_geotiff(output, bad, template)
    assert not output.exists()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or infinity"):
        write_submission_geotiff(output, bad, template)
    assert not output.exists()


def test_writer_refuses_to_overwrite_an_existing_unique_deliverable(tmp_path):
    template = tmp_path / "template.tif"
    _write_template(template)
    output = tmp_path / "existing.tif"
    output.write_bytes(b"previous artifact")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_submission_geotiff(output, np.zeros((6, 8), dtype=np.float32), template)
    assert output.read_bytes() == b"previous artifact"


def test_validator_detects_wrong_shape_and_nodata_sentinel(tmp_path):
    template = tmp_path / "template.tif"
    _write_template(template)
    wrong = tmp_path / "wrong.tif"
    with rasterio.open(
        wrong,
        "w",
        driver="GTiff",
        height=5,
        width=8,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    ) as dst:
        dst.write(np.zeros((5, 8), dtype=np.float32), 1)
    with pytest.raises(ValueError, match="shape_matches_template"):
        validate_geotiff(wrong, template)

    bad = tmp_path / "sentinel.tif"
    values = np.zeros((6, 8), dtype=np.float32)
    values[1, 1] = -3.4028235e38
    with rasterio.open(
        bad,
        "w",
        driver="GTiff",
        height=6,
        width=8,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
    ) as dst:
        dst.write(values, 1)
    with pytest.raises(ValueError, match="range_0_1_all_cells"):
        validate_geotiff(bad, template)
