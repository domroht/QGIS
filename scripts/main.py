import json
from pathlib import Path

from ddm_qa import ddm_qa

PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_DIR / "data"

DYBDE = DATA_DIR / "ddm_study_area_dybde.tif"
KILDE = DATA_DIR / "ddm_study_area_kilde.tif"
AAR = DATA_DIR / "ddm_study_area_aar.tif"

OUTPUT_DIR = PROJECT_DIR / "output"

DYBDE_LOCAL_RANGE = OUTPUT_DIR / "dybde_local_range_3x3.tif"
PL_VARIATION_MASK_FLAGS = OUTPUT_DIR / "pl_variation_mask_flags.tif"
QA_RESULTS_JSON = OUTPUT_DIR / "qa_results.json"


def main():

    rasters = {
        "dybde": DYBDE,
        "kilde": KILDE,
        "aar": AAR,
    }

    qa_results = ddm_qa(
        rasters=rasters,
        local_range_path=DYBDE_LOCAL_RANGE,
        high_variation_path=PL_VARIATION_MASK_FLAGS,
        percentile_limit=95,
    )

    with QA_RESULTS_JSON.open("w", encoding="utf-8") as file:
        json.dump(
            qa_results,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )


if __name__ == "__main__":
    main()