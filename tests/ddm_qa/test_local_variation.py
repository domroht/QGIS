import numpy as np
import pytest
import rasterio
from affine import Affine

from ddm_qa.local_variation import (
    identify_pl_variation_areas,
    analyze_pl_variation_areas,
)


def test_connectivity_4():

    test_mask = np.array([
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 1],
        [0, 0, 0, 1, 0],
    ], dtype=bool)

    labels, areas = identify_pl_variation_areas(
        test_mask,
        connectivity=4,
    )

    assert len(areas) == 4

    assert areas[1]["pixels"] == 1
    assert areas[2]["pixels"] == 1
    assert areas[3]["pixels"] == 1
    assert areas[4]["pixels"] == 1


def test_connectivity_8():

    test_mask = np.array([
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 1],
        [0, 0, 0, 1, 0],
    ], dtype=bool)

    labels, areas = identify_pl_variation_areas(
        test_mask,
        connectivity=8,
    )

    assert len(areas) == 2

    assert areas[1]["pixels"] == 2
    assert areas[2]["pixels"] == 2


def test_invalid_connectivity():

    test_mask = np.array([
        [0, 1, 0],
        [0, 0, 1],
        [0, 0, 0],
    ], dtype=bool)

    with pytest.raises(ValueError):

        identify_pl_variation_areas(
            test_mask,
            connectivity=6,
        )


def test_analyze_high_variation_areas(tmp_path):

    labeled_areas = np.array([
        [0, 1, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 2],
        [0, 0, 0, 2],
    ])

    dybde = np.array([
        [0, 10, 20, 0],
        [0, 30, 40, 0],
        [0, 0, 0, 50],
        [0, 0, 0, 60],
    ], dtype=np.float32)

    kilde = np.array([
        [0, 1, 1, 0],
        [0, 1, 3, 0],
        [0, 0, 0, 8],
        [0, 0, 0, 8],
    ], dtype=np.int32)

    aar = np.array([
        [0, 2000, 2000, 0],
        [0, 2000, 2020, 0],
        [0, 0, 0, 2023],
        [0, 0, 0, 2023],
    ], dtype=np.int32)

    transform = Affine(
        1,
        0,
        0,
        0,
        -1,
        4,
    )

    profile = {
        "driver": "GTiff",
        "height": 4,
        "width": 4,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": 0,
    }

    dybde_path = tmp_path / "dybde.tif"

    with rasterio.open(
        dybde_path,
        "w",
        **profile,
    ) as dst:

        dst.write(dybde, 1)

    kilde_path = tmp_path / "kilde.tif"

    profile["dtype"] = "int32"

    with rasterio.open(
        kilde_path,
        "w",
        **profile,
    ) as dst:

        dst.write(kilde, 1)

    aar_path = tmp_path / "aar.tif"

    with rasterio.open(
        aar_path,
        "w",
        **profile,
    ) as dst:

        dst.write(aar, 1)

    result = analyze_pl_variation_areas(
        dybde_path,
        kilde_path,
        aar_path,
        labeled_areas,
    )

    assert len(result) == 2

    assert result[1]["pixels"] == 4
    assert result[2]["pixels"] == 2

    assert result[1]["depth"]["mean"] == 25
    assert result[1]["depth"]["min"] == 10
    assert result[1]["depth"]["max"] == 40

    assert result[2]["depth"]["mean"] == 55
    assert result[2]["depth"]["min"] == 50
    assert result[2]["depth"]["max"] == 60

    assert result[1]["source_counts"] == {
        1: 3,
        3: 1,
    }

    assert result[2]["source_counts"] == {
        8: 2,
    }

    assert result[1]["year_counts"] == {
        2000: 3,
        2020: 1,
    }

    assert result[2]["year_counts"] == {
        2023: 2,
    }