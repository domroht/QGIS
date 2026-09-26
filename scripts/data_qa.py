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

LOCAL_RANGE = OUTPUT_DIR / "dybde_local_range_3x3.tif"

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

    with rasterio.open(paths["dybde"]) as dybde_raster:
        reference = {
            "shape": dybde_raster.shape,
            "crs": dybde_raster.crs,
            "transform": dybde_raster.transform,
            "resolution": dybde_raster.res,
        }

    results = []

    for name, path in paths.items():

        with rasterio.open(path) as raster:

            checks = {
                "shape": raster.shape == reference["shape"],
                "crs": raster.crs == reference["crs"],
                "transform": raster.transform == reference["transform"],
                "resolution": raster.res == reference["resolution"],
            }

            results.append((name, checks))

    return results

def check_kilde_values(path: Path):

    # ddm data kilder er nummeret mellem 1-8
    valid_kilde_codes = np.arange(1, 9)

    with rasterio.open(path) as kilde_raster:
        kilde = kilde_raster.read(1, masked=True)

    valid_values = np.unique(kilde.compressed())

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

    with rasterio.open(path) as dybde_raster:
        dybde = dybde_raster.read(1, masked=True)

    values = dybde.compressed()

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

def calculate_local_range(input_path: Path, output_path: Path):
    """
    Funktion til at udregne lokal variation mellem en pixel og det omliggende (så 3x3 pixels)
    """

    with rasterio.open(input_path) as raster:

        data = raster.read(1, masked=True)
        profile = raster.profile.copy()

        # Konvater NoData til NaN så vi kan bruge numpy funktionernne .nanmin() og .nanmax() 
        values = data.filled(np.nan).astype(np.float32)


        neighborhoods = []

        # Forskyder rasteren i alle 9 retninger og samler de 9 naboværdier for hver pixel i en ny demition (så: 9 x højde x længde)
        for row_shift in (-1, 0, 1):
            for col_shift in (-1, 0, 1):

                # laver et tomt raster med samme str som input (values)
                shifted = np.full_like(
                    values,
                    np.nan,
                )

                # afgrænser hvilke dele af rasteret vi kan bruge 
                row_start = max(0, row_shift)
                row_end = (
                    values.shape[0]
                    + min(0, row_shift)
                )

                col_start = max(0, col_shift)
                col_end = (
                    values.shape[1]
                    + min(0, col_shift)
                )

                # kopier data fra values ind på de relevante positioner i det tomme raster (shifted[område] = values[område])
                shifted[
                    row_start:row_end,
                    col_start:col_end,
                ] = values[
                    row_start - row_shift:row_end - row_shift,
                    col_start - col_shift:col_end - col_shift,
                ]

                neighborhoods.append(shifted)

        # stacker vores 9 raster til et 3D array
        neighborhood = np.stack(neighborhoods)

        # undlad at give runtime warning ved 3x3 NaN værdier
        with np.errstate(all="ignore"):
            # for hver pixel skal vi sammenligne alle 9 raster for at finde max og min og så trække dem fra hinanden for at finde den største variation i dens omliggende 3x3
            local_min = np.nanmin(
                neighborhood,
                axis=0,
            )

            local_max = np.nanmax(
                neighborhood,
                axis=0,
            )

        local_range = local_max - local_min

        # Kontroller om den oprindelige center pixel i 3x3 havde en ugyldig værdi hvis den have skal den heller ikke have en værdi i vore nye raster med lokal variation
        local_range[~np.isfinite(values)] = np.nan

        # kontroller om hver pixel har en gyldig værdi hvis ikke sætter vi en værdi -9999 (representer en NoData)
        output = np.where(
            np.isfinite(local_range),
            local_range,
            -9999,
        ).astype(np.float32)

        # updater vores kopieret profil
        profile.update(
            dtype="float32",
            nodata=-9999,
            count=1,
            compress="deflate",
        )

        # opretter vores output fil og skriver outputtet til band 1
        with rasterio.open(
            output_path,
            "w",
            **profile,
        ) as dst:

            dst.write(output, 1)

def analyze_local_range(path: Path):

    with rasterio.open(path) as raster:
        data = raster.read(1, masked=True)

    # fjern maskerede pixels (returnere i 1D array)
    values = data.compressed()

    if len(values) == 0:
        return None

    percentiles = np.percentile(
        values,
        [50, 75, 90, 95, 99],
    )

    # retuner statstik på vores lokal variation raster
    return {
        "valid_pixels": len(values),
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "median": float(percentiles[0]),
        "p75": float(percentiles[1]),
        "p90": float(percentiles[2]),
        "p95": float(percentiles[3]),
        "p99": float(percentiles[4]),
        "std": float(values.std()),
    }

def get_pl_variation_mask(path: Path, percentile_limit: int):

    with rasterio.open(path) as raster:
        local_range = raster.read(1, masked=True)

    values = local_range.compressed()

    if len(values) == 0:
        return None

    # udregner grænsen for den givne percentil (gentagelse fra analyze_local_range())
    threshold = np.percentile(
        values,
        percentile_limit,
    )

    # for hver pixel kontroller vi den er gyldig og over den percentile grænse
    variation_mask = (
        ~local_range.mask
        & (local_range.data >= threshold)
    )

    return threshold, variation_mask


def analyze_pl_variation_mask(
    dybde_path: Path,
    kilde_path: Path,
    aar_path: Path,
    range_path: Path,
    percentile_limit: int,
):
    """
    Funktion der skal finde sammenhæg med lokal variation af dybdeværdier over en betstemt percentil grænse 
        - Kigger på hvilken dybde de har, deres data kilde og oprindelses år
        - sammenhæng mellem data kilde og oprindelses år
    """

    threshold, variation_mask = (
        get_pl_variation_mask(range_path, percentile_limit)
    )

    with rasterio.open(dybde_path) as dybde_raster:
        dybde = dybde_raster.read(1, masked=True)

    with rasterio.open(kilde_path) as kilde_rasterc:
        kilde = kilde_rasterc.read(1, masked=True)

    with rasterio.open(aar_path) as aar_raster:
        aar = aar_raster.read(1, masked=True)

    dybde_values = dybde[variation_mask].compressed()
    kilde_values = kilde[variation_mask].compressed()
    aar_values = aar[variation_mask].compressed()

    kilde_counts = {}
    aar_counts = {}

    # defineres in case len(kilde_values) <= 0 bruges senere til at finde kilde_x_aar  
    kilde_unique = []

    if len(kilde_values) > 0:
        # finder hvilke kilder de har (1-8) og hvor mange gange de er der (retuner 2 arrays)
        kilde_unique, kilde_count_values = np.unique(
            kilde_values,
            return_counts=True,
        )
        # omdan de 2 arrays til et dict
        kilde_counts = {
            int(value): int(count)
            for value, count
            in zip(kilde_unique, kilde_count_values)
        }

    if len(aar_values) > 0:

        aar_unique, aar_count_values = np.unique(
            aar_values,
            return_counts=True,
        )

        aar_counts = {
            int(value): int(count)
            for value, count
            in zip(aar_unique, aar_count_values)
        }

    kilde_x_aar = {}

    for kilde_code in kilde_unique:

        # Pixels med: høj lokal variation, gyldig kilde og den aktuelle kildekode
        kilde_mask = (
            variation_mask
            & ~kilde.mask
            & (kilde.data == kilde_code)
        )

        total = int(kilde_mask.sum())

        code_aar = {}

        if total > 0:

            # Find år for de pixels der har et gyldigt år
            aar_values_for_kilde = aar.data[
                kilde_mask
                & ~aar.mask
            ]

            if len(aar_values_for_kilde) > 0:

                unique, counts = np.unique(
                    aar_values_for_kilde,
                    return_counts=True,
                )

                code_aar = {
                    int(value): int(count)
                    for value, count
                    in zip(unique, counts)
                }

        # Hvor mange pixels mangler et gyldigt år?
        missing_aar = (
            kilde_mask
            & aar.mask
        )

        kilde_x_aar[int(kilde_code)] = {
            "total": total,
            "years": code_aar,
            "missing_year": int(missing_aar.sum()),
        }

    return {
        "pl_threshold": float(threshold),
        "variation_mask_pixels": int(
            variation_mask.sum()
        ),
        "depth": {
            "valid_pixels": len(dybde_values),
            "mean": float(dybde_values.mean()),
            "median": float(np.median(dybde_values)),
            "min": float(dybde_values.min()),
            "max": float(dybde_values.max()),
        },
        "source_counts": kilde_counts,
        "year_counts": aar_counts,
        "kilde_aar": kilde_x_aar,
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

    calculate_local_range(
        DYBDE,
        LOCAL_RANGE,
    )

    range_stats = analyze_local_range(
        LOCAL_RANGE
    )

    print(range_stats)

    print("Ran script data_qa.py")

if __name__ == "__main__":
    main()