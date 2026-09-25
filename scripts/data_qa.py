from pathlib import Path

import numpy as np
import rasterio
 
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Inputs paths
DATA_DIR = PROJECT_DIR / "data"

DYBDE = DATA_DIR / "ddm_study_area_dybde.tif"
KILDE = DATA_DIR / "ddm_study_area_kilde.tif"
AAR = DATA_DIR / "ddm_study_area_aar.tif"

# output paths
OUTPUT_DIR = PROJECT_DIR / "output"

def check_required_files(paths: dict[str, Path]):
    
    missing = [
        path
        for path in paths.values()
        if not path.exists()
    ]

    return missing

def validate_inputs(paths: dict[str, Path]):
    
    if not paths:
        print("ERROR: No input rasters specified.")
        raise SystemExit(1)

    missing_files = check_required_files(paths)

    if missing_files:
        print("ERROR: Missing input files:")
        for path in missing_files:
            print(f"  {path}")
        raise SystemExit(1)


def inspect_raster(path: Path):

    with rasterio.open(path) as raster:
        # Læs band 1 for raster og masker NoData
        data = raster.read(1, masked=True)
        # Tæl ikke maskerede værdier
        valid_pixels = int(data.count())

        return {
            "file": path.name,
            "size": (raster.width, raster.height),
            "crs": raster.crs,
            "resolution": raster.res,
            "nodata": raster.nodata,
            "valid_pixels": valid_pixels,
            "min": float(data.min()) if valid_pixels else None,
            "max": float(data.max()) if valid_pixels else None,
            "mean": float(data.mean()) if valid_pixels else None,
        }

def check_grid_consistency(paths: dict[str, Path]):
    """Check that rasters use the same spatial grid."""

    with rasterio.open(paths["dybde"]) as depth:
        reference = {
            "shape": depth.shape,
            "crs": depth.crs,
            "transform": depth.transform,
            "resolution": depth.res,
        }

    results = []

    for name, path in paths.items():

        with rasterio.open(path) as src:

            checks = {
                "shape": src.shape == reference["shape"],
                "crs": src.crs == reference["crs"],
                "transform": src.transform == reference["transform"],
                "resolution": src.res == reference["resolution"],
            }

            results.append((name, checks))

    return results


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rasters: dict[str, Path] = {
        "dybde": DYBDE,
        "kilde": KILDE,
        "aar": AAR,
    }

    validate_inputs(rasters)

    print("Ran script data_qa.py")

if __name__ == "__main__":
    main()