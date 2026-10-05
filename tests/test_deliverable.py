from pathlib import Path
import hashlib
import zipfile
import numpy as np
import rasterio

DELIVERABLE_TIF = Path("docs/downloads/gemsdoe37-topo-persistence-20261005T025021488008Z-58f9ca92.tif")
DELIVERABLE_ZIP = Path("docs/downloads/gemsdoe37-topo-persistence-20261005T025021488008Z-58f9ca92.zip")
EXPECTED_SHA256 = "29ce3150ae796ca50570b830b9231487fc5a043af5b0681f7e7dbe8f4fbdcc19"


def test_published_deliverable_geotiff_exists_and_is_valid():
    assert DELIVERABLE_TIF.exists(), f"Deliverable {DELIVERABLE_TIF} not found"
    
    # Check SHA256
    file_bytes = DELIVERABLE_TIF.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    assert sha256 == EXPECTED_SHA256, f"Expected {EXPECTED_SHA256}, got {sha256}"
    
    # Check GeoTIFF metadata & content
    with rasterio.open(DELIVERABLE_TIF) as src:
        assert src.driver == "GTiff"
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert src.crs.to_epsg() == 32611
        assert src.shape == (3730, 3292)
        assert src.nodata is None
        
        arr = src.read(1)
        assert np.all(np.isfinite(arr)), "All cells must be finite"
        assert np.all((arr >= 0.0) & (arr <= 1.0)), "All cells must be strictly in [0.0, 1.0]"
        assert (arr > 0.0).sum() == 37654, f"Expected 37654 positive pixels, got {(arr > 0.0).sum()}"


def test_published_deliverable_zip_contains_single_geotiff():
    assert DELIVERABLE_ZIP.exists(), f"Deliverable {DELIVERABLE_ZIP} not found"
    with zipfile.ZipFile(DELIVERABLE_ZIP, "r") as zf:
        infolist = zf.infolist()
        assert len(infolist) == 1, "Zip must contain exactly one file"
        assert infolist[0].filename.endswith(".tif")
        extracted_bytes = zf.read(infolist[0])
        extracted_sha256 = hashlib.sha256(extracted_bytes).hexdigest()
        assert extracted_sha256 == EXPECTED_SHA256
