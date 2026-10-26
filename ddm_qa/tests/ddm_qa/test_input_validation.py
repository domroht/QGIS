import numpy as np
import rasterio
from rasterio.transform import Affine

from ddm_qa.input_validation import (
    validate_input_paths,
    validate_grid_consistency,
    validate_kilde_values,
    validate_dybde_values,
    validate_aar_values,
)

def create_raster(path, data, *, crs="EPSG:25832", transform=None, nodata=-9999):
    if transform is None:
        transform = Affine(
            1,
            0,
            0,
            0,
            -1,
            3,
        )

    data = np.asarray(data, dtype=np.float32)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)

def create_valid_rasters(tmp_path):
    paths = {
        "dybde": tmp_path / "dybde.tif",
        "kilde": tmp_path / "kilde.tif",
        "aar": tmp_path / "aar.tif",
    }

    create_raster(
        paths["dybde"],
        [
            [10, 20, 30],
            [15, 25, 35],
            [12, 22, 32],
        ],
    )

    create_raster(
        paths["kilde"],
        [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 1],
        ],
    )

    create_raster(
        paths["aar"],
        [
            [2020, 2021, 2022],
            [2020, 2021, 2022],
            [2020, 2021, 2022],
        ],
    )

    return paths

def test_validate_input_paths_pass(tmp_path):
    paths = create_valid_rasters(tmp_path)

    result = validate_input_paths(paths)

    assert result["status"] == "PASS"
    assert result["missing_files"] == []

def test_validate_input_paths_missing_file(tmp_path):
    paths = create_valid_rasters(tmp_path)

    paths["aar"] = tmp_path / "missing.tif"

    result = validate_input_paths(paths)

    assert result["status"] == "FAIL"
    assert result["missing_files"] == ["aar"]

def test_validate_input_paths_multiple_missing_files(tmp_path):
    paths = create_valid_rasters(tmp_path)

    paths["kilde"] = tmp_path / "missing_kilde.tif"
    paths["aar"] = tmp_path / "missing_aar.tif"

    result = validate_input_paths(paths)

    assert result["status"] == "FAIL"
    assert set(result["missing_files"]) == {"kilde", "aar"}

def test_validate_grid_consistency_pass(tmp_path):
    paths = create_valid_rasters(tmp_path)

    result = validate_grid_consistency(paths)

    assert result["status"] == "PASS"
    assert result["inconsistent_rasters"] == []

def test_validate_grid_consistency_detects_shape_difference(tmp_path):
    paths = create_valid_rasters(tmp_path)

    create_raster(
        paths["kilde"],
        [
            [1, 2],
            [3, 4],
        ],
    )

    result = validate_grid_consistency(paths)

    assert result["status"] == "FAIL"
    assert "kilde" in result["inconsistent_rasters"]

def test_validate_grid_consistency_detects_crs_difference(tmp_path):
    paths = create_valid_rasters(tmp_path)

    create_raster(
        paths["kilde"],
        [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 1],
        ],
        crs="EPSG:4326",
    )

    result = validate_grid_consistency(paths)

    assert result["status"] == "FAIL"
    assert "kilde" in result["inconsistent_rasters"]

def test_validate_grid_consistency_detects_transform_difference(tmp_path):
    paths = create_valid_rasters(tmp_path)

    create_raster(
        paths["aar"],
        [
            [2020, 2021, 2022],
            [2020, 2021, 2022],
            [2020, 2021, 2022],
        ],
        transform=Affine(
            2,
            0,
            0,
            0,
            -2,
            6,
        ),
    )

    result = validate_grid_consistency(paths)

    assert result["status"] == "FAIL"
    assert "aar" in result["inconsistent_rasters"]

def test_validate_grid_consistency_detects_resolution_difference(tmp_path):
    paths = create_valid_rasters(tmp_path)

    create_raster(
        paths["aar"],
        [
            [2020, 2021, 2022],
            [2020, 2021, 2022],
            [2020, 2021, 2022],
        ],
        transform=Affine(
            2,
            0,
            0,
            0,
            -2,
            6,
        ),
    )

    result = validate_grid_consistency(paths)

    assert result["status"] == "FAIL"
    assert "aar" in result["inconsistent_rasters"]

def test_validate_kilde_values_pass(tmp_path):
    path = tmp_path / "kilde.tif"

    create_raster(
        path,
        [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 1],
        ],
    )

    result = validate_kilde_values(path)

    assert result["status"] == "PASS"
    assert result["invalid_values"] == []
    assert result["invalid_pixels"] == 0

def test_validate_kilde_values_detects_invalid_values(tmp_path):
    path = tmp_path / "kilde.tif"

    create_raster(
        path,
        [
            [1, 2, 9],
            [4, 5, 6],
            [7, 8, 0],
        ],
    )

    result = validate_kilde_values(path)

    assert result["status"] == "WARNING"
    assert set(result["invalid_values"]) == {0, 9}
    assert result["invalid_pixels"] == 2

def test_validate_kilde_values_ignores_nodata(tmp_path):
    path = tmp_path / "kilde.tif"

    create_raster(
        path,
        [
            [1, 2, -9999],
            [4, 5, 6],
            [7, 8, 1],
        ],
    )

    result = validate_kilde_values(path)

    assert result["status"] == "PASS"
    assert result["invalid_values"] == []
    assert result["invalid_pixels"] == 0

def test_validate_dybde_values_pass(tmp_path):
    path = tmp_path / "dybde.tif"

    create_raster(
        path,
        [
            [0, 10, 20],
            [15, 25, 35],
            [12, 22, 32],
        ],
    )

    result = validate_dybde_values(path)

    assert result["status"] == "PASS"
    assert result["invalid_pixels"] == 0

def test_validate_dybde_values_detects_negative_values(tmp_path):
    path = tmp_path / "dybde.tif"

    create_raster(
        path,
        [
            [10, -1, 20],
            [15, 25, 35],
            [12, 22, 32],
        ],
    )

    result = validate_dybde_values(path)

    assert result["status"] == "WARNING"
    assert result["invalid_pixels"] == 1

def test_validate_dybde_values_detects_nan(tmp_path):
    path = tmp_path / "dybde.tif"

    create_raster(
        path,
        [
            [10, np.nan, 20],
            [15, 25, 35],
            [12, 22, 32],
        ],
    )

    result = validate_dybde_values(path)

    assert result["status"] == "WARNING"
    assert result["invalid_pixels"] == 1

def test_validate_dybde_values_no_valid_data(tmp_path):
    path = tmp_path / "dybde.tif"

    create_raster(
        path,
        [
            [-9999, -9999],
            [-9999, -9999],
        ],
    )

    result = validate_dybde_values(path)

    assert result["status"] == "FAIL"
    assert result["invalid_pixels"] == 0

def test_validate_aar_values_pass(tmp_path):
    path = tmp_path / "aar.tif"

    create_raster(
        path,
        [
            [2020, 2021, 2022],
            [2020, 2021, 2022],
            [2020, 2021, 2022],
        ],
    )

    result = validate_aar_values(path)

    assert result["status"] == "PASS"
    assert result["invalid_pixels"] == 0

def test_validate_aar_values_detects_zero(tmp_path):
    path = tmp_path / "aar.tif"

    create_raster(
        path,
        [
            [2020, 0, 2022],
            [2020, 2021, 2022],
            [2020, 2021, 2022],
        ],
    )

    result = validate_aar_values(path)

    assert result["status"] == "WARNING"
    assert result["invalid_pixels"] == 1

def test_validate_aar_values_detects_future_year(tmp_path):
    path = tmp_path / "aar.tif"

    create_raster(
        path,
        [
            [2020, 2025, 2022],
            [2020, 2021, 2022],
            [2020, 2021, 2022],
        ],
    )

    result = validate_aar_values(path)

    assert result["status"] == "WARNING"
    assert result["invalid_pixels"] == 1

def test_validate_aar_values_detects_non_integer_year(tmp_path):
    path = tmp_path / "aar.tif"

    create_raster(
        path,
        [
            [2020, 2021.5, 2022],
            [2020, 2021, 2022],
            [2020, 2021, 2022],
        ],
    )

    result = validate_aar_values(path)

    assert result["status"] == "WARNING"
    assert result["invalid_pixels"] == 1

def test_validate_aar_values_no_valid_data(tmp_path):
    path = tmp_path / "aar.tif"

    create_raster(
        path,
        [
            [-9999, -9999],
            [-9999, -9999],
        ],
    )

    result = validate_aar_values(path)

    assert result["status"] == "FAIL"
    assert result["invalid_pixels"] == 0

def test_validate_aar_values_2024_is_valid(tmp_path):
    path = tmp_path / "aar.tif"

    create_raster(
        path,
        [
            [2024, 2023, 2022],
            [2021, 2020, 2019],
            [2018, 2017, 2016],
        ],
    )

    result = validate_aar_values(path)

    assert result["status"] == "PASS"
    assert result["invalid_pixels"] == 0