from pathlib import Path

from .input_validation import (
    validate_input_paths,
    validate_grid_consistency,
    validate_kilde_values,
    validate_dybde_values,
    validate_aar_values,
)

from .input_inspection import (
    get_raster_overview,
    get_value_distribution,
    get_value_percentages,
    get_value_pair_distribution,
    get_raster_statistics,
)

from .local_variation import (
    calculate_local_range,
    get_pl_variation_mask,
    analyze_pl_variation_mask,
    create_pl_variation_mask_flags,
    identify_pl_variation_areas,
    analyze_pl_variation_areas,
)

def ddm_qa(rasters: dict[str, Path], local_range_path: Path, high_variation_path: Path, percentile_limit: int, pl_area_connect: int) -> dict:

    qa_results = {
        "input_validation": {},
        "input_inspection": {},
        "local_variation": {},
        "outputs": {},
    }

    #=====================================#
    #==         INPUT VALIDATION        ==#
    #=====================================#

    qa_results["input_validation"]["paths"] = (
        validate_input_paths(rasters)
    )

    if qa_results["input_validation"]["paths"]["status"] == "FAIL":
        return qa_results

    qa_results["input_validation"]["grid"] = (
        validate_grid_consistency(rasters)
    )

    if qa_results["input_validation"]["grid"]["status"] == "FAIL":
        return qa_results


    qa_results["input_validation"]["kilde"] = (
        validate_kilde_values(rasters["kilde"])
    )

    qa_results["input_validation"]["dybde"] = (
        validate_dybde_values(rasters["dybde"])
    )

    qa_results["input_validation"]["aar"] = (
        validate_aar_values(rasters["aar"])
    )

    #=====================================#
    #==         INPUT INSPECTION        ==#
    #=====================================#

    for name, path in rasters.items():

        qa_results["input_inspection"][name] = {
            "overview": get_raster_overview(path),
            "statistics": get_raster_statistics(path),
        }
        
        # springer dybde over med distribution da det har meget præcise måle værdier (mange unikke float værdier)
        if name in ("kilde", "aar"):

            distribution = get_value_distribution(path)

            qa_results["input_inspection"][name]["distribution"] = (
                distribution
            )

            qa_results["input_inspection"][name]["percentages"] = (
                get_value_percentages(distribution)
            )

    qa_results["input_inspection"]["kilde_aar"] = (
        get_value_pair_distribution(
            rasters["kilde"],
            rasters["aar"],
        )
    )

    #=====================================#
    #==         LOCAL VARIATION         ==#
    #=====================================#

    calculate_local_range(
        rasters["dybde"],
        local_range_path,
    )

    qa_results["local_variation"]["statistics"] = (
        get_raster_statistics(local_range_path)
    )

    threshold, variation_mask = get_pl_variation_mask(
        local_range_path,
        percentile_limit,
    )

    qa_results["local_variation"]["analysis"] = (
        analyze_pl_variation_mask(
            rasters["dybde"],
            rasters["kilde"],
            rasters["aar"],
            variation_mask,
            threshold,
        )
    )

    labeled_areas, areas = identify_pl_variation_areas(
        variation_mask,
        connectivity=pl_area_connect,
    )

    area_analysis = analyze_pl_variation_areas(
        rasters["dybde"],
        rasters["kilde"],
        rasters["aar"],
        labeled_areas,
    )

    qa_results["local_variation"]["areas"] = {
        "connectivity": pl_area_connect,
        "count": len(areas),
        "areas": area_analysis,
    }

    #=====================================#
    #==          DDM QA OUTPUT          ==#
    #=====================================#

    qa_results["outputs"]["local_range"] = {
        "path": local_range_path,
    }

    flags_result = create_pl_variation_mask_flags(
        rasters["dybde"],
        variation_mask,
        high_variation_path,
    )

    qa_results["outputs"]["high_variation"] = flags_result

    return qa_results