import numpy as np
import rasterio
from rasterio.transform import Affine

from ddm_qa.input_inspection import (
    get_raster_overview,
    get_raster_statistics,
    get_value_distribution,
    get_value_percentages,
    get_value_pair_distribution,
    get_raster_metadata,
    get_raster_metadata_collection,
)

def create_raster(path, data, *, nodata=-9999, crs="EPSG:25832", transform=None):

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

def test_get_raster_overview(tmp_path):
    path = tmp_path / "test.tif"

    create_raster(
        path,
        [
            [1, 2, 3],
            [4, 5, -9999],
        ],
    )

    result = get_raster_overview(path)

    assert result["file"] == "test.tif"
    assert result["size"] == [3, 2]
    assert result["dtype"] == "float32"
    assert result["crs"] == "EPSG:25832"

    assert result["total_pixels"] == 6
    assert result["valid_pixels"] == 5
    assert result["nodata_pixels"] == 1

    assert result["valid_percentage"] == 5 / 6 * 100

    assert result["min"] == 1.0
    assert result["max"] == 5.0
    assert result["mean"] == 3.0

    assert result["nodata"] == -9999

def test_get_raster_overview_all_nodata(tmp_path):
    path = tmp_path / "nodata.tif"

    create_raster(
        path,
        [
            [-9999, -9999],
            [-9999, -9999],
        ],
    )

    result = get_raster_overview(path)

    assert result["total_pixels"] == 4
    assert result["valid_pixels"] == 0
    assert result["nodata_pixels"] == 4
    assert result["valid_percentage"] == 0
    assert result["min"] is None
    assert result["max"] is None
    assert result["mean"] is None

def test_get_raster_statistics(tmp_path):
    path = tmp_path / "statistics.tif"

    create_raster(
        path,
        [
            [1, 2, 3],
            [4, 5, -9999],
        ],
    )

    result = get_raster_statistics(path)

    values = np.array([1, 2, 3, 4, 5], dtype=float)

    assert result["valid_pixels"] == 5
    assert result["min"] == 1.0
    assert result["max"] == 5.0
    assert result["mean"] == 3.0
    assert result["median"] == 3.0

    assert result["p75"] == np.percentile(values, 75)
    assert result["p90"] == np.percentile(values, 90)
    assert result["p95"] == np.percentile(values, 95)
    assert result["p99"] == np.percentile(values, 99)

    assert np.isclose(
        result["std"],
        values.std(),
    )

def test_get_raster_statistics_all_nodata(tmp_path):
    path = tmp_path / "empty.tif"

    create_raster(
        path,
        [
            [-9999, -9999],
            [-9999, -9999],
        ],
    )

    result = get_raster_statistics(path)

    assert result == {}

def test_get_value_distribution(tmp_path):
    path = tmp_path / "distribution.tif"

    create_raster(
        path,
        [
            [1, 1, 2],
            [2, 2, 3],
            [3, -9999, 3],
        ],
    )

    result = get_value_distribution(path)

    assert result == {
        1: 2,
        2: 3,
        3: 3,
    }

def test_get_value_distribution_all_nodata(tmp_path):
    path = tmp_path / "empty.tif"

    create_raster(
        path,
        [
            [-9999, -9999],
            [-9999, -9999],
        ],
    )

    result = get_value_distribution(path)

    assert result == {}

def test_get_value_percentages():
    distribution = {
        1: 2,
        2: 3,
        3: 5,
    }

    result = get_value_percentages(distribution)

    assert result == {
        1: 20.0,
        2: 30.0,
        3: 50.0,
    }

def test_get_value_percentages_empty():
    result = get_value_percentages({})

    assert result == {}

def test_get_value_pair_distribution(tmp_path):
    first_path = tmp_path / "kilde.tif"
    second_path = tmp_path / "aar.tif"

    create_raster(
        first_path,
        [
            [1, 1, 2],
            [2, 2, 3],
        ],
    )

    create_raster(
        second_path,
        [
            [2020, 2021, 2020],
            [2020, 2020, 2021],
        ],
    )

    result = get_value_pair_distribution(
        first_path,
        second_path,
    )

    assert result == {
        1: {
            2020: 1,
            2021: 1,
        },
        2: {
            2020: 3,
        },
        3: {
            2021: 1,
        },
    }

def test_get_value_pair_distribution_respects_nodata(tmp_path):
    first_path = tmp_path / "first.tif"
    second_path = tmp_path / "second.tif"

    create_raster(
        first_path,
        [
            [1, 1],
            [1, -9999],
        ],
    )

    create_raster(
        second_path,
        [
            [2020, -9999],
            [2020, 2021],
        ],
    )

    result = get_value_pair_distribution(
        first_path,
        second_path,
    )

    assert result == {
        1: {
            2020: 2,
        },
    }

def test_get_value_pair_distribution_no_valid_pairs(tmp_path):
    first_path = tmp_path / "first.tif"
    second_path = tmp_path / "second.tif"

    create_raster(
        first_path,
        [
            [-9999, -9999],
        ],
    )

    create_raster(
        second_path,
        [
            [2020, 2021],
        ],
    )

    result = get_value_pair_distribution(
        first_path,
        second_path,
    )

    assert result == {}

def test_get_raster_metadata(tmp_path):
    path = tmp_path / "metadata.tif"

    create_raster(
        path,
        [
            [1, 2],
            [3, 4],
        ],
    )

    with rasterio.open(path, "r+") as raster:
        raster.update_tags(
            source="test",
            description="Test raster",
        )

    result = get_raster_metadata(path)

    assert result["file"] == "metadata.tif"
    assert result["driver"] == "GTiff"
    assert result["count"] == 1
    assert result["dtype"] == "float32"
    assert result["crs"] == "EPSG:25832"
    assert result["nodata"] == -9999

    assert result["descriptions"] == [None]
    assert result["units"] == [None]
    assert result["scales"] == [1.0]
    assert result["offsets"] == [0.0]

    assert result["tags"]["source"] == "test"
    assert result["tags"]["description"] == "Test raster"

def test_get_raster_metadata_with_band_metadata(tmp_path):
    path = tmp_path / "band_metadata.tif"

    create_raster(
        path,
        [
            [1, 2],
            [3, 4],
        ],
    )

    with rasterio.open(path, "r+") as raster:
        raster.set_band_description(
            1,
            "Depth",
        )

        raster.set_band_unit(
            1,
            "metres",
        )

    result = get_raster_metadata(path)

    assert result["descriptions"] == ["Depth"]
    assert result["units"] == ["metres"]

def test_get_raster_metadata_collection(tmp_path):
    paths = {
        "dybde": tmp_path / "dybde.tif",
        "kilde": tmp_path / "kilde.tif",
        "aar": tmp_path / "aar.tif",
    }

    create_raster(
        paths["dybde"],
        [
            [10, 20],
            [30, 40],
        ],
    )

    create_raster(
        paths["kilde"],
        [
            [1, 2],
            [3, 4],
        ],
    )

    create_raster(
        paths["aar"],
        [
            [2020, 2021],
            [2022, 2023],
        ],
    )

    result = get_raster_metadata_collection(paths)

    assert set(result.keys()) == {
        "dybde",
        "kilde",
        "aar",
    }

    assert result["dybde"]["file"] == "dybde.tif"
    assert result["kilde"]["file"] == "kilde.tif"
    assert result["aar"]["file"] == "aar.tif"