from ddm_qa.qa_observations import (
    create_observation,
    evaluate_validation_observations,
    evaluate_completeness_observations,
    evaluate_local_variation_observations,
    evaluate_source_year_observations,
    evaluate_depth_range_observations,
    evaluate_metadata_observations,
    evaluate_all_observations,
)

def test_create_observation_basic():
    result = create_observation(
        code="TEST",
        status="PASS",
        message="Everything is OK.",
    )

    assert result == {
        "code": "TEST",
        "status": "PASS",
        "message": "Everything is OK.",
    }

def test_create_observation_with_value():
    result = create_observation(
        code="TEST",
        status="INFO",
        message="Test value.",
        value=42,
    )

    assert result["value"] == 42

def test_create_observation_with_details():
    result = create_observation(
        code="TEST",
        status="WARNING",
        message="Test details.",
        details={"pixels": 10},
    )

    assert result["details"] == {"pixels": 10}

def test_evaluate_validation_observations_pass():
    input_validation = {
        "grid": {"status": "PASS"},
        "kilde": {"status": "PASS"},
        "dybde": {"status": "PASS"},
        "aar": {"status": "PASS"},
    }

    result = evaluate_validation_observations(
        input_validation
    )

    assert len(result) == 4

    codes = {observation["code"] for observation in result}

    assert codes == {
        "GRID_CONSISTENCY",
        "INVALID_SOURCE_CODES",
        "INVALID_DEPTH_VALUES",
        "INVALID_YEAR_VALUES",
    }

    assert all(
        observation["status"] == "PASS"
        for observation in result
    )

def test_evaluate_validation_observations_warning():
    input_validation = {
        "kilde": {
            "status": "WARNING",
            "invalid_values": [0, 9],
            "invalid_pixels": 5,
        }
    }

    result = evaluate_validation_observations(
        input_validation
    )

    assert len(result) == 1

    observation = result[0]

    assert observation["code"] == "INVALID_SOURCE_CODES"
    assert observation["status"] == "WARNING"
    assert observation["details"] == {
        "invalid_values": [0, 9],
        "invalid_pixels": 5,
    }

def test_evaluate_validation_observations_fail():
    input_validation = {
        "grid": {
            "status": "FAIL",
            "inconsistent_rasters": ["kilde"],
        }
    }

    result = evaluate_validation_observations(
        input_validation
    )

    assert len(result) == 1

    observation = result[0]

    assert observation["code"] == "GRID_CONSISTENCY"
    assert observation["status"] == "FAIL"
    assert observation["details"] == {
        "inconsistent_rasters": ["kilde"],
    }

def test_evaluate_validation_observations_ignores_missing_results():
    result = evaluate_validation_observations({})

    assert result == []

def test_evaluate_completeness_observations():
    input_inspection = {
        "dybde": {
            "overview": {
                "valid_percentage": 99.1234,
            }
        },
        "kilde": {
            "overview": {
                "valid_percentage": 98.5678,
            }
        },
        "aar": {
            "overview": {
                "valid_percentage": 97.1111,
            }
        },
    }

    result = evaluate_completeness_observations(
        input_inspection
    )

    assert len(result) == 3

    observations = {
        observation["code"]: observation
        for observation in result
    }

    assert observations["DEPTH_COMPLETENESS"]["value"] == 99.12
    assert observations["SOURCE_COMPLETENESS"]["value"] == 98.57
    assert observations["YEAR_COMPLETENESS"]["value"] == 97.11

    assert all(
        observation["status"] == "INFO"
        for observation in result
    )

def test_evaluate_completeness_observations_ignores_missing_percentage():
    input_inspection = {
        "dybde": {
            "overview": {}
        }
    }

    result = evaluate_completeness_observations(
        input_inspection
    )

    assert result == []

def test_evaluate_local_variation_observations():
    local_variation = {
        "percentile": 95,
        "analysis": {
            "variation_mask_pixels": 125,
            "pl_threshold": 4.5,
        },
        "areas": {
            "count": 7,
            "connectivity": 8,
        },
    }

    result = evaluate_local_variation_observations(
        local_variation
    )

    assert len(result) == 2

    observations = {
        observation["code"]: observation
        for observation in result
    }

    local_observation = observations["PL_LOCAL_VARIATION"]

    assert local_observation["status"] == "WARNING"
    assert local_observation["value"] == 125
    assert local_observation["details"] == {
        "percentile": 95,
        "threshold": 4.5,
    }

    area_observation = observations["PL_VARIATION_AREAS"]

    assert area_observation["status"] == "WARNING"
    assert area_observation["value"] == 7
    assert area_observation["details"] == {
        "connectivity": 8,
    }

def test_evaluate_local_variation_observations_empty():
    result = evaluate_local_variation_observations({})

    assert result == []

def test_evaluate_source_year_observations_source_mixture():
    local_variation = {
        "areas": {
            "areas": {
                "1": {
                    "source_counts": {
                        1: 10,
                        2: 5,
                    },
                    "year_counts": {
                        2020: 15,
                    },
                },
                "2": {
                    "source_counts": {
                        3: 20,
                    },
                    "year_counts": {
                        2020: 10,
                        2021: 10,
                    },
                },
            }
        }
    }

    input_inspection = {}

    result = evaluate_source_year_observations(
        local_variation,
        input_inspection,
    )

    observations = {
        observation["code"]: observation
        for observation in result
    }

    assert observations["SOURCE_MIXTURE"]["value"] == 1
    assert observations["SOURCE_MIXTURE"]["details"] == {
        "area_ids": [1]
    }

    assert observations["YEAR_MIXTURE"]["value"] == 1
    assert observations["YEAR_MIXTURE"]["details"] == {
        "area_ids": [2]
    }

def test_evaluate_source_year_observations_missing_years():
    local_variation = {
        "areas": {
            "areas": {}
        }
    }

    input_inspection = {
        "kilde": {
            "distribution": {
                1: 100,
                2: 50,
            }
        },
        "kilde_aar": {
            1: {
                2020: 80,
            },
            2: {
                2021: 50,
            },
        },
    }

    result = evaluate_source_year_observations(
        local_variation,
        input_inspection,
    )

    assert len(result) == 1

    observation = result[0]

    assert observation["code"] == "MISSING_SOURCE_YEARS"
    assert observation["status"] == "WARNING"
    assert observation["value"] == 1

    assert observation["details"]["sources"] == [
        {
            "source": 1,
            "pixels_without_year": 20,
            "pixels_with_year": 80,
            "year_completeness": 80.0,
        }
    ]

def test_evaluate_source_year_observations_no_issues():
    local_variation = {
        "areas": {
            "areas": {
                "1": {
                    "source_counts": {
                        1: 10,
                    },
                    "year_counts": {
                        2020: 10,
                    },
                }
            }
        }
    }

    input_inspection = {
        "kilde": {
            "distribution": {
                1: 10,
            }
        },
        "kilde_aar": {
            1: {
                2020: 10,
            }
        },
    }

    result = evaluate_source_year_observations(
        local_variation,
        input_inspection,
    )

    assert result == []

def test_evaluate_depth_range_observations():
    local_variation = {
        "areas": {
            "areas": {
                "1": {
                    "depth": {
                        "range": 5.5,
                        "min": 10.0,
                        "max": 15.5,
                    }
                },
                "2": {
                    "depth": {
                        "range": 2.0,
                        "min": 20.0,
                        "max": 22.0,
                    }
                },
            }
        }
    }

    result = evaluate_depth_range_observations(
        local_variation
    )

    assert len(result) == 1

    observation = result[0]

    assert observation["code"] == "DEPTH_RANGE_IN_PL_VARIATION_AREAS"
    assert observation["status"] == "INFO"
    assert observation["value"] == 2

    assert observation["details"]["areas"] == [
        {
            "area_id": 1,
            "range": 5.5,
            "min": 10.0,
            "max": 15.5,
        },
        {
            "area_id": 2,
            "range": 2.0,
            "min": 20.0,
            "max": 22.0,
        },
    ]

def test_evaluate_depth_range_observations_empty():
    result = evaluate_depth_range_observations({})

    assert result == []

def test_evaluate_metadata_observations_limited_metadata():
    metadata = {
        "dybde": {
            "tags": {},
            "descriptions": [None],
            "units": [None],
        },
        "kilde": {
            "tags": {"source": "test"},
            "descriptions": [None],
            "units": [None],
        },
    }

    result = evaluate_metadata_observations(
        metadata
    )

    assert len(result) == 1

    observation = result[0]

    assert observation["code"] == "LIMITED_METADATA"
    assert observation["status"] == "WARNING"
    assert observation["value"] == 1
    assert observation["details"] == {
        "rasters": ["dybde"]
    }

def test_evaluate_metadata_observations_complete_metadata():
    metadata = {
        "dybde": {
            "tags": {"source": "test"},
            "descriptions": [None],
            "units": [None],
        },
        "kilde": {
            "tags": {},
            "descriptions": ["Source raster"],
            "units": [None],
        },
        "aar": {
            "tags": {},
            "descriptions": [None],
            "units": ["year"],
        },
    }

    result = evaluate_metadata_observations(
        metadata
    )

    assert result == []

def test_evaluate_all_observations():
    input_validation = {
        "grid": {"status": "PASS"},
        "kilde": {"status": "PASS"},
        "dybde": {"status": "PASS"},
        "aar": {"status": "PASS"},
    }

    input_inspection = {
        "dybde": {
            "overview": {
                "valid_percentage": 99.5,
            }
        },
        "kilde": {
            "overview": {
                "valid_percentage": 98.0,
            },
        },
        "aar": {
            "overview": {
                "valid_percentage": 97.0,
            },
        },
        "kilde_aar": {
            1: {
                2020: 10,
            }
        },
    }

    metadata = {
        "dybde": {
            "tags": {"source": "test"},
            "descriptions": [None],
            "units": [None],
        }
    }

    local_variation = {
        "percentile": 95,
        "analysis": {
            "variation_mask_pixels": 20,
            "pl_threshold": 3.5,
        },
        "areas": {
            "count": 2,
            "connectivity": 8,
            "areas": {
                "1": {
                    "source_counts": {1: 10},
                    "year_counts": {2020: 10},
                    "depth": {
                        "range": 4.0,
                        "min": 10.0,
                        "max": 14.0,
                    },
                }
            },
        },
    }

    result = evaluate_all_observations(
        input_validation,
        input_inspection,
        metadata,
        local_variation,
    )

    codes = {
        observation["code"]
        for observation in result
    }

    assert "GRID_CONSISTENCY" in codes
    assert "INVALID_SOURCE_CODES" in codes
    assert "INVALID_DEPTH_VALUES" in codes
    assert "INVALID_YEAR_VALUES" in codes

    assert "DEPTH_COMPLETENESS" in codes
    assert "SOURCE_COMPLETENESS" in codes
    assert "YEAR_COMPLETENESS" in codes

    assert "PL_LOCAL_VARIATION" in codes
    assert "PL_VARIATION_AREAS" in codes

    assert "DEPTH_RANGE_IN_PL_VARIATION_AREAS" in codes