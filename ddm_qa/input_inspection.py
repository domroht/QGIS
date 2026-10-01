from pathlib import Path

import numpy as np
import rasterio
 

def get_raster_overview(path: Path) -> dict:

    with rasterio.open(path) as raster:

        data = raster.read(1, masked=True)

        valid_pixels = int(data.count())
        total_pixels = raster.width * raster.height
        nodata_pixels = total_pixels - valid_pixels

        # kan tilføje flere ting hvis nødvendig 
        return {
            "file": path.name,
            "size": [raster.width, raster.height],
            "dtype": raster.dtypes[0],
            "crs": str(raster.crs),
            "resolution": list(raster.res),
            "bounds": {
                "left": raster.bounds.left,
                "bottom": raster.bounds.bottom,
                "right": raster.bounds.right,
                "top": raster.bounds.top,
            },
            "nodata": raster.nodata,
            "total_pixels": total_pixels,
            "valid_pixels": valid_pixels,
            "nodata_pixels": nodata_pixels,
            "valid_percentage": (
                valid_pixels / total_pixels * 100
                if total_pixels
                else 0
            ),
            "min": float(data.min()) if valid_pixels else None,
            "max": float(data.max()) if valid_pixels else None,
            "mean": float(data.mean()) if valid_pixels else None,
        }

def get_raster_statistics(path: Path) -> dict:

    with rasterio.open(path) as raster:
        data = raster.read(1, masked=True)

    values = data.compressed()

    if len(values) == 0:
        return {}

    percentiles = np.percentile(
        values,
        [50, 75, 90, 95, 99],
    )

    return {
        "valid_pixels": int(len(values)),
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

def get_value_distribution(path: Path) -> dict:

    with rasterio.open(path) as raster:
        data = raster.read(1, masked=True)

    values = data.compressed()

    if len(values) == 0:
        return {}

    unique, counts = np.unique(
        values,
        return_counts=True,
    )

    return {
        int(value): int(count)
        for value, count in zip(unique, counts)
    }

def get_value_percentages(distribution: dict) -> dict:

    total = sum(distribution.values())

    if total == 0:
        return {}

    return {
        value: count / total * 100
        for value, count in distribution.items()
    }

def get_value_pair_distribution(first_path: Path, second_path: Path) -> dict:

    with rasterio.open(first_path) as first_raster:
        first = first_raster.read(1, masked=True)

    with rasterio.open(second_path) as second_raster:
        second = second_raster.read(1, masked=True)

    valid = (
        ~first.mask
        & ~second.mask
    )

    first_values = first.data[valid]
    second_values = second.data[valid]

    if len(first_values) == 0:
        return {}

    pairs = np.column_stack(
        (first_values, second_values)
    )

    unique_pairs, counts = np.unique(
        pairs,
        axis=0,
        return_counts=True,
    )

    result = {}

    for pair, count in zip(unique_pairs, counts):

        first_value = int(pair[0])
        second_value = int(pair[1])

        result.setdefault(
            first_value,
            {},
        )[second_value] = int(count)

    return result

def get_raster_metadata(path: Path) -> dict:

    with rasterio.open(path) as raster:
        default_tags = raster.tags()
        namespaces = raster.tag_namespaces()

        namespace_tags = {}

        for namespace in namespaces:
            namespace_tags[namespace] = raster.tags(ns=namespace)

        band_descriptions = list(raster.descriptions)
        band_units = list(raster.units)
        band_scales = list(raster.scales)
        band_offsets = list(raster.offsets)

        return {
            "file": path.name,
            "driver": raster.driver,
            "count": raster.count,
            "dtype": raster.dtypes[0],
            "crs": str(raster.crs) if raster.crs else None,
            "nodata": raster.nodata,
            "descriptions": band_descriptions,
            "units": band_units,
            "scales": band_scales,
            "offsets": band_offsets,
            "tags": default_tags,
            "tag_namespaces": namespaces,
            "namespace_tags": namespace_tags,
        }

def get_raster_metadata_collection(paths: dict[str, Path]) -> dict:

    metadata = {}

    for name, path in paths.items():
        metadata[name] = get_raster_metadata(path)

    return metadata
