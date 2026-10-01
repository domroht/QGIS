def create_observation(code: str, status: str, message: str,value=None, details=None) -> dict:

    observation = {
        "code": code,
        "status": status,
        "message": message,
    }

    if value is not None:
        observation["value"] = value

    if details is not None:
        observation["details"] = details

    return observation

def evaluate_validation_observations(input_validation: dict,) -> list[dict]:

    observations = []

    validation_mapping = {
        "grid": (
            "GRID_CONSISTENCY",
            "Raster grids er konsistense",
            "Raster grids er ikke konsistente",
        ),
        "kilde": (
            "INVALID_SOURCE_CODES",
            "Alle kilde koder er valide",
            "Fandt kilde kode der ikke er valide ~(1-8)",
        ),
        "dybde": (
            "INVALID_DEPTH_VALUES",
            "Alle dybde værdier er valide",
            "Fandt dybde værdier der er negative eller ikke finite",
        ),
        "aar": (
            "INVALID_YEAR_VALUES",
            "Alle års værdier er valide",
            "fandt års værdier der ikke er valide",
        ),
    }

    for name, (
        code,
        pass_message,
        problem_message,
    ) in validation_mapping.items():

        result = input_validation.get(name)

        if not result:
            continue

        status = result["status"]

        if status == "PASS":
            observations.append(
                create_observation(
                    code=code,
                    status="PASS",
                    message=pass_message,
                )
            )

        elif status in ("WARNING", "FAIL"):
            observations.append(
                create_observation(
                    code=code,
                    status=status,
                    message=problem_message,
                    details={
                        key: value
                        for key, value in result.items()
                        if key not in ("status", "message")
                    },
                )
            )

    return observations

def evaluate_completeness_observations(input_inspection: dict) -> list[dict]:

    observations = []

    completeness_mapping = {
        "dybde": "DEPTH_COMPLETENESS",
        "kilde": "SOURCE_COMPLETENESS",
        "aar": "YEAR_COMPLETENESS",
    }

    for raster_name, code in completeness_mapping.items():

        raster_result = input_inspection.get(raster_name)

        if not raster_result:
            continue

        overview = raster_result.get("overview", {})

        percentage = overview.get(
            "valid_percentage"
        )

        if percentage is None:
            continue

        observations.append(
            create_observation(
                code=code,
                status="INFO",
                message=(
                    f"{raster_name.capitalize()} "
                    f"har en data komplethed på: "
                    f"{percentage:.2f}%."
                ),
                value=round(
                    percentage,
                    2,
                ),
            )
        )

    return observations

def evaluate_local_variation_observations(local_variation: dict) -> list[dict]:

    observations = []

    analysis = local_variation.get("analysis",{})

    areas = local_variation.get("areas",{})

    variation_pixels = analysis.get("variation_mask_pixels")

    threshold = analysis.get("pl_threshold")

    area_count = areas.get("count")

    if variation_pixels is not None:
        observations.append(
            create_observation(
                code="HIGH_LOCAL_VARIATION",
                status="WARNING",
                message=("Fandt pixels med lokal variation over den percentile grænse"),
                value=variation_pixels,
                details={
                    "percentile": 95,
                    "threshold": threshold,
                },
            )
        )

    if area_count is not None:
        observations.append(
            create_observation(
                code="HIGH_VARIATION_AREAS",
                status="WARNING",
                message=("Fandt Sammenhængende områder med lokal variation over den percentile grænse"),
                value=area_count,
                details={
                    "connectivity": areas.get(
                        "connectivity"
                    ),
                },
            )
        )

    return observations

def evaluate_source_year_observations(local_variation: dict, input_inspection: dict) -> list[dict]:

    observations = []

    areas = local_variation.get("areas", {}).get("areas", {})

    source_mixture_areas = []
    year_mixture_areas = []

    for area_id, area in areas.items():
        source_counts = area.get("source_counts", {})
        year_counts = area.get("year_counts", {})

        if len(source_counts) > 1:
            source_mixture_areas.append(int(area_id))

        if len(year_counts) > 1:
            year_mixture_areas.append(int(area_id))

    if source_mixture_areas:
        observations.append(create_observation(
            code="SOURCE_MIXTURE",
            status="WARNING",
            message=("Områder med lokal variation over percentile grænse, indeholder flere forskellige kilde koder"),
            value=len(source_mixture_areas),
            details={"area_ids": source_mixture_areas},
        ))

    if year_mixture_areas:
        observations.append(create_observation(
            code="YEAR_MIXTURE",
            status="WARNING",
            message=("Områder med lokal variation over percentile grænse, indeholder flere forskellige kilde år"),
            value=len(year_mixture_areas),
            details={"area_ids": year_mixture_areas},
        ))

    kilde_aar = input_inspection.get("kilde_aar", {})
    kilde_distribution = (
        input_inspection
        .get("kilde", {})
        .get("distribution", {})
    )

    missing_year_sources = []

    for source, source_total in kilde_distribution.items():
        source_total = int(source_total)

        year_data = kilde_aar.get(source, {})
        pixels_with_year = sum(
            int(count)
            for count in year_data.values()
        )

        missing_year = source_total - pixels_with_year

        if missing_year > 0:
            completeness = (
                pixels_with_year / source_total * 100
                if source_total
                else 0
            )

            missing_year_sources.append({
                "source": int(source),
                "pixels_without_year": missing_year,
                "pixels_with_year": pixels_with_year,
                "year_completeness": round(completeness, 2),
            })

    if missing_year_sources:
        observations.append(create_observation(
            code="MISSING_SOURCE_YEARS",
            status="WARNING",
            message=("Fandt data kilder der indeholder pixels uden et kilde år"),
            value=len(missing_year_sources),
            details={"sources": missing_year_sources},
        ))

    return observations

def evaluate_depth_range_observations(local_variation: dict) -> list[dict]:

    observations = []

    areas = local_variation.get(
        "areas",
        {}
    ).get(
        "areas",
        {}
    )

    areas_with_depth = []

    for area_id, area in areas.items():

        depth = area.get(
            "depth"
        )

        if not depth:
            continue

        areas_with_depth.append(
            {
                "area_id": int(area_id),
                "range": depth.get("range"),
                "min": depth.get("min"),
                "max": depth.get("max"),
            }
        )

    if areas_with_depth:

        observations.append(
            create_observation(
                code="DEPTH_RANGE_IN_HIGH_VARIATION_AREAS",
                status="INFO",
                message=("Udregnede dybde variationen i områder med lokal variation over den percentile grænse"),
                value=len(areas_with_depth),
                details={"areas": areas_with_depth},
            )
        )

    return observations

def evaluate_metadata_observations(metadata: dict) -> list[dict]:

    observations = []

    rasters_with_limited_metadata = []

    for raster_name, raster_metadata in metadata.items():
        tags = raster_metadata.get("tags", {})
        descriptions = raster_metadata.get("descriptions", [])
        units = raster_metadata.get("units", [])

        has_description = any(
            description is not None
            for description in descriptions
        )

        has_tags = bool(tags)

        has_units = any(
            unit is not None
            for unit in units
        )

        if not has_description and not has_tags and not has_units:
            rasters_with_limited_metadata.append(raster_name)

    if rasters_with_limited_metadata:
        observations.append(create_observation(
            code="LIMITED_METADATA",
            status="WARNING",
            message=("Fandt en eller flere raster med manglende metadata"),
            value=len(rasters_with_limited_metadata),
            details={"rasters": rasters_with_limited_metadata},
        ))

    return observations

def evaluate_all_observations(input_validation: dict, input_inspection: dict, metadata: dict, local_variation: dict) -> list[dict]:

    observations = []

    observations.extend(
        evaluate_validation_observations(
            input_validation
        )
    )

    observations.extend(
        evaluate_completeness_observations(
            input_inspection
        )
    )

    observations.extend(
        evaluate_metadata_observations(metadata)
    )

    observations.extend(
        evaluate_local_variation_observations(
            local_variation
        )
    )

    observations.extend(
        evaluate_source_year_observations(
            local_variation,
            input_inspection,
        )
    )
    observations.extend(
        evaluate_depth_range_observations(
            local_variation
        )
    )

    return observations


