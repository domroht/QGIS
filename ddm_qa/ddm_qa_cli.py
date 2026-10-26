from pathlib import Path
import argparse
import json

from ddm_qa.ddm_qa import ddm_qa


def main():
    parser = argparse.ArgumentParser(
        description="Run DDM QA engine."
    )

    parser.add_argument(
        "--dybde",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--kilde",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--aar",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--local-range",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--pl-variation",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--pl-variation-areas",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--percentile-limit",
        type=int,
        default=95,
    )

    parser.add_argument(
        "--pl-area-connect",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--result-json",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--report-html",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    args.result_json.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.report_html.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Starting DDM QA...")
    print(f"Dybde: {args.dybde}")
    print(f"Kilde: {args.kilde}")
    print(f"År: {args.aar}")
    print(f"Connectivity: {args.pl_area_connect}")
    print(f"Percentile: {args.percentile_limit}")

    results = ddm_qa(
        rasters={
            "dybde": args.dybde,
            "kilde": args.kilde,
            "aar": args.aar,
        },
        local_range_path=args.local_range,
        pl_variation_path=args.pl_variation,
        pl_variation_areas_path=args.pl_variation_areas,
        report_path=args.report_html,
        report_figure_dir=args.report_html.parent / "report_figures",
        percentile_limit=args.percentile_limit,
        pl_area_connect=args.pl_area_connect,
    )

    with args.result_json.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print("DDM QA completed.")


if __name__ == "__main__":
    main()