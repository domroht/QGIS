from pathlib import Path

import numpy as np
import rasterio


def validate_input_paths(paths: dict[str, Path]) -> dict:

    missing_paths = [
        name
        for name, path in paths.items()
        if not path.is_file()
    ]

    if missing_paths:

        return {
            "status": "FAIL",
            "message": "One or more input files are missing.",
            "missing_files": missing_paths,
        }

    return {
        "status": "PASS",
        "message": "All input files exist.",
        "missing_files": [],
    }

def validate_grid_consistency(paths: dict[str, Path]) -> dict:

    with rasterio.open(paths["dybde"]) as reference:

        reference_shape = reference.shape
        reference_crs = reference.crs
        reference_transform = reference.transform
        reference_res = reference.res

        inconsistent_rasters = []

        for name, path in paths.items():

            with rasterio.open(path) as raster:

                if (
                    raster.shape != reference_shape
                    or raster.crs != reference_crs
                    or raster.transform != reference_transform
                    or raster.res != reference_res
                ):
                    inconsistent_rasters.append(name)

    if inconsistent_rasters:

        return {
            "status": "FAIL",
            "message": "Raster grids are not consistent.",
            "inconsistent_rasters": inconsistent_rasters,
        }

    return {
        "status": "PASS",
        "message": "All raster grids are consistent.",
        "inconsistent_rasters": [],
    }

def validate_kilde_values(path: Path) -> dict:

    valid_kilde_codes = np.arange(1, 9)

    with rasterio.open(path) as kilde_raster:
        kilde = kilde_raster.read(1, masked=True)

    values = np.unique(kilde.compressed())

    invalid_values = values[
        ~np.isin(values, valid_kilde_codes)
    ]

    if len(invalid_values) > 0:

        invalid_pixels = int(
            np.sum(
                ~np.isin(
                    kilde.compressed(),
                    valid_kilde_codes,
                )
            )
        )

        return {
            "status": "WARNING",
            "message": "Unexpected source codes were found.",
            "invalid_values": [
                int(value)
                for value in invalid_values
            ],
            "invalid_pixels": invalid_pixels,
        }

    return {
        "status": "PASS",
        "message": "All source codes are valid.",
        "invalid_values": [],
        "invalid_pixels": 0,
    }

def validate_dybde_values(path: Path) -> dict:

    with rasterio.open(path) as dybde_raster:
        dybde = dybde_raster.read(1, masked=True)

    values = dybde.compressed()

    invalid_mask = (
        ~np.isfinite(values)
        | (values < 0)
    )

    invalid_pixels = int(
        np.sum(invalid_mask)
    )

    if len(values) == 0:

        return {
            "status": "FAIL",
            "message": "No valid depth values were found.",
            "invalid_pixels": 0,
        }

    if invalid_pixels > 0:

        return {
            "status": "WARNING",
            "message": "Invalid depth values were found.",
            "invalid_pixels": invalid_pixels,
        }

    return {
        "status": "PASS",
        "message": "All depth values are valid.",
        "invalid_pixels": 0,
    }

def validate_aar_values(path: Path) -> dict:

    with rasterio.open(path) as aar_raster:
        aar = aar_raster.read(1, masked=True)

    values = aar.compressed()

    if len(values) == 0:

        return {
            "status": "FAIL",
            "message": "No valid year values were found.",
            "invalid_pixels": 0,
        }

    invalid_mask = (
        ~np.isfinite(values)
        | (values != values.astype(int))
        | (values <= 0)
        | (values <= 2024)
    )

    invalid_pixels = int(
        np.sum(invalid_mask)
    )

    if invalid_pixels > 0:

        return {
            "status": "WARNING",
            "message": "Invalid year values were found.",
            "invalid_pixels": invalid_pixels,
        }

    return {
        "status": "PASS",
        "message": "All year values are valid.",
        "invalid_pixels": 0,
    }

