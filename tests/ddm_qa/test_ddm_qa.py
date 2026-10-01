import numpy as np
import rasterio
from rasterio.transform import Affine
from pathlib import Path

from ddm_qa.ddm_qa import ddm_qa

def create_raster(path, data, nodata=-9999):
    data = np.asarray(data, dtype=np.float32)

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:25832",
        transform=Affine(
            1,
            0,
            0,
            0,
            -1,
            3,
        ),
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)

def create_valid_dataset(tmp_path):
    rasters = {
        "dybde": tmp_path / "dybde.tif",
        "kilde": tmp_path / "kilde.tif",
        "aar": tmp_path / "aar.tif",
    }

    create_raster(
        rasters["dybde"],
        [
            [10, 10, 10],
            [10, 20, 10],
            [10, 10, 10],
        ],
    )

    create_raster(
        rasters["kilde"],
        [
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 1],
        ],
    )

    create_raster(
        rasters["aar"],
        [
            [2020, 2020, 2020],
            [2020, 2020, 2020],
            [2020, 2020, 2020],
        ],
    )

    return rasters

def test_ddm_qa_runs_successfully(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    local_range_path = tmp_path / "local_range.tif"
    pl_variation_path = tmp_path / "pl_variation.tif"
    pl_variation_areas_path = tmp_path / "pl_variation_areas.tif"
    report_path = tmp_path / "qa_report.html"

    result = ddm_qa(
        rasters=rasters,
        local_range_path=local_range_path,
        pl_variation_path=pl_variation_path,
        pl_variation_areas_path=pl_variation_areas_path,
        report_path=report_path,
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    assert isinstance(result, dict)

    assert "input_validation" in result
    assert "input_inspection" in result
    assert "metadata" in result
    assert "local_variation" in result
    assert "observations" in result
    assert "outputs" in result

def test_ddm_qa_validation_passes(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    result = ddm_qa(
        rasters=rasters,
        local_range_path=tmp_path / "local_range.tif",
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    validation = result["input_validation"]

    assert validation["paths"]["status"] == "PASS"
    assert validation["grid"]["status"] == "PASS"
    assert validation["kilde"]["status"] == "PASS"
    assert validation["dybde"]["status"] == "PASS"
    assert validation["aar"]["status"] == "PASS"

def test_ddm_qa_creates_local_range_output(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    local_range_path = tmp_path / "local_range.tif"

    result = ddm_qa(
        rasters=rasters,
        local_range_path=local_range_path,
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    assert local_range_path.is_file()
    assert result["outputs"]["local_range"]["path"] == local_range_path

def test_ddm_qa_creates_variation_outputs(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    local_range_path = tmp_path / "local_range.tif"
    pl_variation_path = tmp_path / "pl_variation.tif"
    pl_variation_areas_path = tmp_path / "pl_variation_areas.tif"

    result = ddm_qa(
        rasters=rasters,
        local_range_path=local_range_path,
        pl_variation_path=pl_variation_path,
        pl_variation_areas_path=pl_variation_areas_path,
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    assert pl_variation_path.is_file()
    assert pl_variation_areas_path.is_file()

    assert "pl_variation" in result["outputs"]
    assert "pl_variation_areas" in result["outputs"]

def test_ddm_qa_creates_report(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    report_path = tmp_path / "qa_report.html"
    report_figure_dir = tmp_path / "report_figures"

    result = ddm_qa(
        rasters=rasters,
        local_range_path=tmp_path / "local_range.tif",
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=report_path,
        report_figure_dir=report_figure_dir,
        percentile_limit=95,
        pl_area_connect=8,
    )

    assert report_path.is_file()
    assert result["outputs"]["report"]["path"] == report_path
    assert report_figure_dir.is_dir()

def test_ddm_qa_local_variation_contains_analysis(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    result = ddm_qa(
        rasters=rasters,
        local_range_path=tmp_path / "local_range.tif",
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    local_variation = result["local_variation"]

    assert local_variation["percentile"] == 95
    assert "statistics" in local_variation
    assert "analysis" in local_variation
    assert "areas" in local_variation

    assert local_variation["areas"]["connectivity"] == 8

def test_ddm_qa_creates_observations(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    result = ddm_qa(
        rasters=rasters,
        local_range_path=tmp_path / "local_range.tif",
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    observations = result["observations"]

    assert isinstance(observations, list)
    assert len(observations) > 0

    codes = {
        observation["code"]
        for observation in observations
    }

    assert "GRID_CONSISTENCY" in codes
    assert "INVALID_SOURCE_CODES" in codes
    assert "INVALID_DEPTH_VALUES" in codes
    assert "INVALID_YEAR_VALUES" in codes

def test_ddm_qa_stops_when_input_file_is_missing(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    rasters["aar"] = tmp_path / "missing.tif"

    result = ddm_qa(
        rasters=rasters,
        local_range_path=tmp_path / "local_range.tif",
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    assert result["input_validation"]["paths"]["status"] == "FAIL"

    assert result["input_inspection"] == {}
    assert result["metadata"] == {}
    assert result["local_variation"] == {}
    assert result["observations"] == []

def test_ddm_qa_stops_when_grid_is_inconsistent(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    create_raster(
        rasters["kilde"],
        [
            [1, 1],
            [1, 1],
        ],
    )

    result = ddm_qa(
        rasters=rasters,
        local_range_path=tmp_path / "local_range.tif",
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=95,
        pl_area_connect=8,
    )

    assert result["input_validation"]["paths"]["status"] == "PASS"
    assert result["input_validation"]["grid"]["status"] == "FAIL"

    assert result["input_inspection"] == {}
    assert result["metadata"] == {}
    assert result["local_variation"] == {}
    assert result["observations"] == []

def test_ddm_qa_uses_requested_percentile_and_connectivity(tmp_path):
    rasters = create_valid_dataset(tmp_path)

    result = ddm_qa(
        rasters=rasters,
        local_range_path=tmp_path / "local_range.tif",
        pl_variation_path=tmp_path / "pl_variation.tif",
        pl_variation_areas_path=tmp_path / "pl_variation_areas.tif",
        report_path=tmp_path / "qa_report.html",
        report_figure_dir=tmp_path / "report_figures",
        percentile_limit=90,
        pl_area_connect=4,
    )

    assert result["local_variation"]["percentile"] == 90
    assert result["local_variation"]["areas"]["connectivity"] == 4