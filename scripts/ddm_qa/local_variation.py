from pathlib import Path
from scipy.ndimage import generate_binary_structure, label

import numpy as np
import rasterio


def calculate_local_range(input_path: Path, output_path: Path) -> None:
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

        valid_neighborhood = np.isfinite(neighborhood)

        has_valid_neighbor = valid_neighborhood.any(axis=0)

        local_min = np.full(
            values.shape,
            np.nan,
            dtype=np.float32,
        )

        local_max = np.full(
            values.shape,
            np.nan,
            dtype=np.float32,
        )

        local_min[has_valid_neighbor] = np.nanmin(
            neighborhood[:, has_valid_neighbor],
            axis=0,
        )

        local_max[has_valid_neighbor] = np.nanmax(
            neighborhood[:, has_valid_neighbor],
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

def get_pl_variation_mask(path: Path, percentile_limit: int) -> tuple[float, np.ndarray] | None:

    with rasterio.open(path) as raster:
        local_range = raster.read(1, masked=True)

    values = local_range.compressed()

    if len(values) == 0:
        return None

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

def analyze_pl_variation_mask(dybde_path: Path, kilde_path: Path, aar_path: Path, variation_mask: np.ndarray, threshold: float) -> dict:
    """
    Funktion der skal finde sammenhæg med lokal variation af dybdeværdier over en betstemt percentil grænse 
        - Kigger på hvilken dybde de har, deres data kilde og oprindelses år
        - sammenhæng mellem data kilde og oprindelses år
    """

    with rasterio.open(dybde_path) as dybde_raster:
        dybde = dybde_raster.read(1, masked=True)

    with rasterio.open(kilde_path) as kilde_raster:
        kilde = kilde_raster.read(1, masked=True)

    with rasterio.open(aar_path) as aar_raster:
        aar = aar_raster.read(1, masked=True)

    # Udvælg kun værdier fra pixels fra vores variation mask
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

        # Finder hvor mange pixels der mangler et gyldigt år
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
            "valid_pixels": int(len(dybde_values)),
            "mean": float(dybde_values.mean()),
            "median": float(np.median(dybde_values)),
            "min": float(dybde_values.min()),
            "max": float(dybde_values.max()),
        },
        "source_counts": kilde_counts,
        "year_counts": aar_counts,
        "kilde_aar": kilde_x_aar,
    }

def create_pl_variation_mask_flags(dybde_path: Path, variation_mask: np.ndarray, output_path: Path) -> dict:

    with rasterio.open(dybde_path) as dybde_raster:

        dybde = dybde_raster.read(1, masked=True)
        profile = dybde_raster.profile.copy()

    # omdan til binær om der er mask eller ej
    flags = np.where(
        variation_mask,
        1,
        0,
    ).astype(np.uint8)

    flags[dybde.mask] = 255

    profile.update(
        dtype="uint8",
        nodata=255,
        count=1,
        compress="deflate",
    )

    with rasterio.open(
        output_path,
        "w",
        **profile,
    ) as dst:

        dst.write(flags, 1)

    return {
        "flagged_pixels": int(
            np.sum(flags == 1)
        ),
        "output": output_path,
    }

def identify_pl_variation_areas(variation_mask: np.ndarray, connectivity: int) -> tuple[np.ndarray, dict]:

    if connectivity not in (4, 8):
        raise ValueError("Connectivity must be either 4 or 8.")

    if connectivity == 4:
        structure = generate_binary_structure(
            rank=2,
            connectivity=1,
        )

    else:
        structure = generate_binary_structure(
            rank=2,
            connectivity=2,
        )

    labeled_areas, area_count = label(
        variation_mask,
        structure=structure,
    )

    areas = {}

    for area_id in range(1, area_count + 1):

        pixel_count = int(
            np.sum(labeled_areas == area_id)
        )

        areas[area_id] = {
            "pixels": pixel_count,
        }

    return labeled_areas, areas

def analyze_pl_variation_areas(dybde_path: Path, kilde_path: Path, aar_path: Path, labeled_areas: np.ndarray) -> dict:
    """
    For hvert område beregnes:
        - antal pixels i området
        - antal gyldige dybdepixels
        - antal gyldige kildepixels
        - antal gyldige årspixels
        - dybde-statistik
        - fordeling af datakilder
        - fordeling af år
    """

    with rasterio.open(dybde_path) as dybde_raster:
        dybde = dybde_raster.read(1, masked=True)

    with rasterio.open(kilde_path) as kilde_raster:
        kilde = kilde_raster.read(1, masked=True)

    with rasterio.open(aar_path) as aar_raster:
        aar = aar_raster.read(1, masked=True)

    areas = {}

    area_ids = np.unique(labeled_areas)

    for area_id in area_ids:

        if area_id == 0:
            continue

        area_mask = (
            labeled_areas == area_id
        )

        pixel_count = int(
            area_mask.sum()
        )

        dybde_values = dybde[
            area_mask
        ].compressed()

        kilde_values = kilde[
            area_mask
        ].compressed()

        aar_values = aar[
            area_mask
        ].compressed()

        area_result = {
            "pixels": pixel_count,

            "valid_depth_pixels": int(
                len(dybde_values)
            ),
            "valid_depth_percentage": (
                len(dybde_values) / pixel_count * 100
                if pixel_count > 0
                else 0
            ),

            "valid_source_pixels": int(
                len(kilde_values)
            ),
            "valid_source_percentage": (
                len(kilde_values) / pixel_count * 100
                if pixel_count > 0
                else 0
            ),

            "valid_year_pixels": int(
                len(aar_values)
            ),
            "valid_year_percentage": (
                len(aar_values) / pixel_count * 100
                if pixel_count > 0
                else 0
            ),
        }

        if len(dybde_values) > 0:
            
            area_result["depth"] = {
                "mean": float(dybde_values.mean()),
                "median": float(np.median(dybde_values)),
                "min": float(dybde_values.min()),
                "max": float(dybde_values.max()),
                "range": float(dybde_values.max() - dybde_values.min()),
            }

        if len(kilde_values) > 0:

            unique, counts = np.unique(
                kilde_values,
                return_counts=True,
            )

            area_result["source_counts"] = {
                int(value): int(count)
                for value, count
                in zip(unique, counts)
            }

        if len(aar_values) > 0:

            unique, counts = np.unique(
                aar_values,
                return_counts=True,
            )

            area_result["year_counts"] = {
                int(value): int(count)
                for value, count
                in zip(unique, counts)
            }

        areas[int(area_id)] = area_result

    return areas

def create_pl_variation_areas_raster(dybde_path: Path, labeled_areas: np.ndarray,output_path: Path) -> dict:

    with rasterio.open(dybde_path) as dybde_raster:
        dybde = dybde_raster.read(1, masked=True)
        profile = dybde_raster.profile.copy()

    area_raster = np.where(
        labeled_areas > 0,
        labeled_areas,
        0,
    ).astype(np.uint16)

    area_raster[dybde.mask] = 255

    profile.update(
        dtype="uint16",
        nodata=255,
        count=1,
        compress="deflate",
    )

    with rasterio.open(
        output_path,
        "w",
        **profile,
    ) as dst:

        dst.write(area_raster, 1)

    return {
        "area_count": int(
            np.max(labeled_areas)
        ),
        "output": output_path,
    }