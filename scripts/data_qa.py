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

def check_kilde_values(path: Path):

    # ddm data kilder er nummeret mellem 1-8
    valid_kilde_codes = np.arange(1, 9)

    with rasterio.open(path) as kilde_raster:
        source = kilde_raster.read(1, masked=True)

    valid_values = np.unique(source.compressed())

    # Find de valide værdier i kilde_raster og lav en liste med alle der ikke er en del a de valide kilde koder
    invalid_values = valid_values[
        ~np.isin(valid_values, valid_kilde_codes)
    ]

    passed = len(invalid_values) == 0

    return {
        "passed": passed,
        "valid_values": valid_values.astype(int).tolist(),
        "invalid_values": invalid_values.astype(int).tolist(),
    }


def check_dybde_values(path: Path):

    with rasterio.open(path) as src:
        depth = src.read(1, masked=True)

    values = depth.compressed()

    negative_pixels = int(
        np.sum(values < 0)
    )

    nonfinite_pixels = int(
        np.sum(~np.isfinite(values))
    )

    passed = (
        len(values) > 0
        and negative_pixels == 0
        and nonfinite_pixels == 0
    )

    return {
        "passed": passed,
        "valid_pixels": len(values),
        "negative_pixels": negative_pixels,
        "nonfinite_pixels": nonfinite_pixels,
    }


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rasters: dict[str, Path] = {
        "dybde": DYBDE,
        "kilde": KILDE,
        "aar": AAR,
    }

    validate_inputs(rasters)

    kilde_check = check_kilde_values(rasters["kilde"])
    dybde_check = check_dybde_values(rasters["dybde"])

    print("Ran script data_qa.py")

if __name__ == "__main__":
    main()