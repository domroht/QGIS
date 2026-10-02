import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
import rasterio


def escape(value) -> str:
    return html.escape(str(value))

def format_number(value, decimals=2) -> str:
    if value is None:
        return "—"

    if isinstance(value, float):
        return f"{value:.{decimals}f}"

    return f"{value:,}"

def status_class(status: str) -> str:
    return {
        "PASS": "pass",
        "INFO": "info",
        "WARNING": "warning",
        "FAIL": "fail",
    }.get(status, "unknown")

def build_status_summary(observations: list[dict]) -> dict:

    summary = {
        "PASS": 0,
        "INFO": 0,
        "WARNING": 0,
        "FAIL": 0,
    }

    for observation in observations:
        status = observation.get("status")

        if status in summary:
            summary[status] += 1

    return summary

def render_status_badge(status: str) -> str:

    return (
        f'<span class="status {status_class(status)}">'
        f"{escape(status)}"
        "</span>"
    )

def render_completeness_table(input_inspection: dict) -> str:

    rows = []

    names = {
        "dybde": "Dybde",
        "kilde": "Kilde",
        "aar": "År",
    }

    for raster_name, display_name in names.items():
        result = input_inspection.get(
            raster_name,
            {},
        )

        overview = result.get(
            "overview",
            {},
        )

        rows.append(
            f"""
            <tr>
                <td>{escape(display_name)}</td>

                <td>{format_number(
                    overview.get("total_pixels"),
                    0
                )}</td>

                <td>{format_number(
                    overview.get("valid_pixels"),
                    0
                )}</td>

                <td>{format_number(
                    overview.get("nodata_pixels"),
                    0
                )}</td>

                <td>{format_number(
                    overview.get("valid_percentage")
                )}%</td>
            </tr>
            """
        )

    return "\n".join(rows)

def render_source_distribution(input_inspection: dict) -> str:

    source = input_inspection.get(
        "kilde",
        {},
    )

    distribution = source.get(
        "distribution",
        {},
    )

    percentages = source.get(
        "percentages",
        {},
    )

    rows = []

    for code, count in distribution.items():
        percentage = percentages.get(code)

        if percentage is None:
            percentage = percentages.get(
                str(code)
            )

        rows.append(
            f"""
            <tr>
                <td>{escape(code)}</td>

                <td>{format_number(
                    count,
                    0
                )}</td>

                <td>{format_number(
                    percentage
                )}%</td>
            </tr>
            """
        )

    return "\n".join(rows)

def render_observations(observations: list[dict]) -> str:

    rows = []

    for observation in observations:
        code = observation.get(
            "code",
            "",
        )

        status = observation.get(
            "status",
            "",
        )

        message = observation.get(
            "message",
            "",
        )

        value = observation.get(
            "value",
        )

        details = observation.get(
            "details",
        )

        detail_html = ""

        if details:
            details_json = json.dumps(
                details,
                indent=2,
                ensure_ascii=False,
            )

            detail_html = (
                "<details>"
                "<summary>Detaljer</summary>"
                f"<pre>{escape(details_json)}</pre>"
                "</details>"
            )

        value_html = (
            "—"
            if value is None
            else escape(value)
        )

        rows.append(
            f"""
            <tr>
                <td><code>{escape(code)}</code></td>

                <td>
                    {render_status_badge(status)}
                </td>

                <td>{escape(message)}</td>

                <td>{value_html}</td>

                <td>{detail_html}</td>
            </tr>
            """
        )

    return "\n".join(rows)

def render_metadata_table( metadata: dict) -> str:

    rows = []

    for raster_name, raster in metadata.items():
        tags = raster.get(
            "tags",
            {},
        )

        software = tags.get(
            "TIFFTAG_SOFTWARE",
            "—",
        )

        datetime = tags.get(
            "TIFFTAG_DATETIME",
            "—",
        )

        descriptions = ", ".join(
            str(value)
            for value in raster.get(
                "descriptions",
                [],
            )
            if value is not None
        )

        units = ", ".join(
            str(value)
            for value in raster.get(
                "units",
                [],
            )
            if value is not None
        )

        rows.append(
            f"""
            <tr>
                <td>{escape(raster_name)}</td>
                <td>{escape(raster.get("driver"))}</td>
                <td>{escape(raster.get("dtype"))}</td>
                <td>{escape(raster.get("crs"))}</td>
                <td>{escape(descriptions or "—")}</td>
                <td>{escape(units or "—")}</td>
                <td>{escape(software)}</td>
                <td>{escape(datetime)}</td>
            </tr>
            """
        )

    return "\n".join(rows)

def render_outputs(outputs: dict) -> str:

    rows = []

    for name, result in outputs.items():
        if isinstance(result, dict):
            path = (
                result.get("output")
                or result.get("path")
            )

            flagged_pixels = result.get(
                "flagged_pixels"
            )

            area_count = result.get(
                "area_count"
            )

            if flagged_pixels is not None:
                value = flagged_pixels
            else:
                value = area_count
        else:
            path = result
            value = None

        value_html = (
            "—"
            if value is None
            else escape(value)
        )

        rows.append(
            f"""
            <tr>
                <td>{escape(name)}</td>

                <td>
                    <code>
                        {escape(path or "—")}
                    </code>
                </td>

                <td>{value_html}</td>
            </tr>
            """
        )

    return "\n".join(rows)

def create_completeness_figure(input_inspection: dict, figure_path: Path) -> None:

    names = {
        "dybde": "Dybde",
        "kilde": "Kilde",
        "aar": "År",
    }

    labels = []
    values = []

    for raster_name, display_name in names.items():
        overview = (
            input_inspection
            .get(raster_name, {})
            .get("overview", {})
        )

        percentage = overview.get(
            "valid_percentage"
        )

        if percentage is not None:
            labels.append(display_name)
            values.append(percentage)

    fig, ax = plt.subplots(
        figsize=(8, 5)
    )

    bars = ax.bar(
        labels,
        values,
    )

    ax.set_title(
        "Datakomplethed"
    )

    ax.set_ylabel(
        "Gyldige pixels (%)"
    )

    ax.set_ylim(
        0,
        100,
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    for bar, value in zip(
        bars,
        values,
    ):
        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 1,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
        )

    fig.tight_layout()

    fig.savefig(
        figure_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

def create_source_distribution_figure(input_inspection: dict, figure_path: Path) -> None:

    source = input_inspection.get(
        "kilde",
        {},
    )

    percentages = source.get(
        "percentages",
        {},
    )

    labels = []
    values = []

    for code, percentage in percentages.items():
        labels.append(
            f"Kilde {code}"
        )

        values.append(
            percentage
        )

    fig, ax = plt.subplots(
        figsize=(9, 5)
    )

    bars = ax.bar(
        labels,
        values,
    )

    ax.set_title(
        "Fordeling af datakilder"
    )

    ax.set_ylabel(
        "Andel af gyldige pixels (%)"
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    for bar, value in zip(
        bars,
        values,
    ):
        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 1,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
        )

    fig.tight_layout()

    fig.savefig(
        figure_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

def create_observation_figure(observations: list[dict], figure_path: Path) -> None:

    summary = build_status_summary(
        observations
    )

    labels = [
        "PASS",
        "INFO",
        "WARNING",
        "FAIL",
    ]

    values = [
        summary[label]
        for label in labels
    ]

    fig, ax = plt.subplots(
        figsize=(8, 5)
    )

    bars = ax.bar(
        labels,
        values,
    )

    ax.set_title(
        "QA-observationer efter status"
    )

    ax.set_ylabel(
        "Antal observationer"
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    for bar, value in zip(
        bars,
        values,
    ):
        ax.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 0.05,
            str(value),
            ha="center",
            va="bottom",
        )

    fig.tight_layout()

    fig.savefig(
        figure_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

def create_high_variation_figure(results: dict, local_range_path: Path, pl_variation_areas_path: Path, figure_path: Path) -> None:

    if not local_range_path.is_file():
        raise FileNotFoundError(
            "Local range raster was not found: "
            f"{local_range_path}"
        )

    if not pl_variation_areas_path.is_file():
        raise FileNotFoundError(
            "PL variation areas raster was not found: "
            f"{pl_variation_areas_path}"
        )

    with rasterio.open(
        local_range_path
    ) as local_range_raster:

        local_range = local_range_raster.read(
            1,
            masked=True,
        )

        local_transform = (
            local_range_raster.transform
        )

        local_bounds = (
            local_range_raster.bounds
        )

        local_crs = local_range_raster.crs

    with rasterio.open(
        pl_variation_areas_path
    ) as areas_raster:

        areas = areas_raster.read(1)

        areas_transform = (
            areas_raster.transform
        )

        areas_bounds = (
            areas_raster.bounds
        )

        areas_crs = areas_raster.crs

        areas_nodata = areas_raster.nodata

    if local_range.shape != areas.shape:
        raise ValueError(
            "Local range and PL variation areas "
            "have different shapes."
        )

    if local_transform != areas_transform:
        raise ValueError(
            "Local range and PL variation areas "
            "have different transforms."
        )

    if local_crs != areas_crs:
        raise ValueError(
            "Local range and PL variation areas "
            "have different CRS."
        )

    if local_bounds != areas_bounds:
        raise ValueError(
            "Local range and PL variation areas "
            "have different bounds."
        )

    local_variation = results.get(
        "local_variation",
        {},
    )

    analysis = local_variation.get(
        "analysis",
        {},
    )

    areas_info = local_variation.get(
        "areas",
        {},
    )

    threshold = analysis.get(
        "pl_threshold"
    )

    percentile = local_variation.get(
        "percentile"
    )

    area_count = areas_info.get(
        "count"
    )

    connectivity = areas_info.get(
        "connectivity"
    )

    fig, ax = plt.subplots(
        figsize=(11, 7),
    )

    ax.set_facecolor("#d9ead3")

    extent = (
        local_bounds.left,
        local_bounds.right,
        local_bounds.bottom,
        local_bounds.top,
    )

    image = ax.imshow(
        local_range,
        extent=extent,
        origin="upper",
        cmap="Blues",
        alpha=1,
        interpolation="nearest",
    )

    colorbar = fig.colorbar(
        image,
        ax=ax,
        fraction=0.046,
        pad=0.04,
    )

    colorbar.set_label(
        "Lokal range (m)"
    )

    area_mask = areas > 0

    if areas_nodata is not None:
        area_mask &= (
            areas != areas_nodata
        )

    area_ids = np.unique(
        areas[area_mask]
    ).astype(int)

    if len(area_ids) > 0:

        base_colors = (
            plt.colormaps["tab20"].resampled(
                len(area_ids)
            )
        )

        area_colors = base_colors(
            np.arange(len(area_ids))
        )

        area_cmap = ListedColormap(
            area_colors
        )

        area_index = np.full(
            areas.shape,
            np.nan,
            dtype=float,
        )

        for index, area_id in enumerate(
            area_ids
        ):
            area_index[
                areas == area_id
            ] = index

        ax.imshow(
            area_index,
            extent=extent,
            origin="upper",
            cmap=area_cmap,
            alpha=1,
            interpolation="nearest",
        )

    ax.set_title(
        "Lokal variation og high-variation områder"
    )

    ax.set_xlabel(
        "Østlig koordinat (m)"
    )

    ax.set_ylabel(
        "Nordlig koordinat (m)"
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    info_lines = []

    if threshold is not None:
        if percentile is not None:
            info_lines.append(
                f"{percentile}-percentil: "
                f"{threshold:.2f} m"
            )
        else:
            info_lines.append(
                f"Percentilgrænse: "
                f"{threshold:.2f} m"
            )

    if area_count is not None:
        info_lines.append(
            f"High-variation områder: "
            f"{area_count}"
        )

    if connectivity is not None:
        info_lines.append(
            f"Connectivity: {connectivity}"
        )

    if info_lines:
        ax.text(
            0.02,
            0.02,
            "\n".join(info_lines),
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="bottom",
            bbox={
                "boxstyle": "round",
                "facecolor": "white",
                "alpha": 0.85,
            },
        )

    if local_crs:
        ax.text(
            0.99,
            0.01,
            f"CRS: {local_crs}",
            transform=ax.transAxes,
            fontsize=8,
            color="white",
            horizontalalignment="right",
            verticalalignment="bottom",
            bbox={
                "boxstyle": "round",
                "facecolor": "black",
                "alpha": 0.55,
            },
        )

    fig.tight_layout()

    fig.savefig(
        figure_path,
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

def create_figures(results: dict, figure_dir: Path, local_range_path: Path, pl_variation_areas_path: Path) -> dict:

    figure_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    completeness_path = (
        figure_dir / "data_completeness.png"
    )

    source_path = (
        figure_dir / "source_distribution.png"
    )

    observation_path = (
        figure_dir / "qa_observations.png"
    )

    high_variation_path = (
        figure_dir / "high_variation_areas.png"
    )

    input_inspection = results.get(
        "input_inspection",
        {},
    )

    observations = results.get(
        "observations",
        [],
    )

    create_completeness_figure(
        input_inspection,
        completeness_path,
    )

    create_source_distribution_figure(
        input_inspection,
        source_path,
    )

    create_observation_figure(
        observations,
        observation_path,
    )

    create_high_variation_figure(
        results,
        local_range_path,
        pl_variation_areas_path,
        high_variation_path,
    )

    return {
        "data_completeness": completeness_path,
        "source_distribution": source_path,
        "qa_observations": observation_path,
        "high_variation_areas": high_variation_path,
    }

def render_report(results: dict, figure_paths: dict) -> str:

    observations = results.get(
        "observations",
        [],
    )

    summary = build_status_summary(
        observations
    )

    input_validation = results.get(
        "input_validation",
        {},
    )

    input_inspection = results.get(
        "input_inspection",
        {},
    )

    metadata = results.get(
        "metadata",
        {},
    )

    outputs = results.get(
        "outputs",
        {},
    )

    local_variation = results.get(
        "local_variation",
        {},
    )

    analysis = local_variation.get(
        "analysis",
        {},
    )

    areas = local_variation.get(
        "areas",
        {},
    )

    statistics = local_variation.get(
        "statistics",
        {},
    )

    completeness_figure = figure_paths[
        "data_completeness"
    ]

    source_figure = figure_paths[
        "source_distribution"
    ]

    observation_figure = figure_paths[
        "qa_observations"
    ]

    high_variation_figure = figure_paths[
        "high_variation_areas"
    ]

    # Rapporten skal kunne flyttes samlet.
    # Derfor bruges relative paths til figurerne.
    report_dir = Path(
        figure_paths[
            "data_completeness"
        ]
    ).parent.parent

    def relative_figure_path(figure_path: Path) -> str:
        return str(
            Path(figure_path).relative_to(
                report_dir
            )
        )

    completeness_src = relative_figure_path(
        completeness_figure
    )

    source_src = relative_figure_path(
        source_figure
    )

    observation_src = relative_figure_path(
        observation_figure
    )

    high_variation_src = relative_figure_path(
        high_variation_figure
    )

    percentile = local_variation.get(
        "percentile"
    )

    threshold = analysis.get(
        "pl_threshold"
    )

    if percentile is not None:
        percentile_label = (
            f"{percentile}-percentil"
        )
    else:
        percentile_label = (
            "Percentilgrænse"
        )

    return f"""<!DOCTYPE html>

<html lang="da">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>DDM – QA Report</title>

<style>

:root {{
    --background: #f5f7fa;
    --surface: #ffffff;
    --border: #d9dee7;
    --text: #202733;
    --muted: #657080;

    --pass: #237a45;
    --info: #2366a8;
    --warning: #a15c00;
    --fail: #a52929;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;

    background: var(--background);<!-- Dette er en kommentar -->
    color: var(--text);

    font-family:
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;

    line-height: 1.5;
}}

main {{
    max-width: 1200px;

    margin: 0 auto;

    padding:
        40px
        24px
        60px;
}}

h1 {{
    margin-bottom: 4px;
}}

h2 {{
    margin-top: 40px;

    border-bottom:
        1px solid var(--border);

    padding-bottom: 8px;
}}

.subtitle {{
    color: var(--muted);
    margin-top: 0;
}}

.summary {{
    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 12px;

    margin: 28px 0;
}}

.summary-card {{
    background: var(--surface);

    border:
        1px solid var(--border);

    border-radius: 8px;

    padding: 18px;
}}

.summary-card .number {{
    font-size: 28px;
    font-weight: 700;
}}

.summary-card .label {{
    color: var(--muted);

    font-size: 14px;
}}

.pass .number {{
    color: var(--pass);
}}

.info .number {{
    color: var(--info);
}}

.warning .number {{
    color: var(--warning);
}}

.fail .number {{
    color: var(--fail);
}}

.section {{
    background: var(--surface);

    border:
        1px solid var(--border);

    border-radius: 8px;

    padding: 24px;

    margin-top: 20px;
}}

.figure {{
    margin:
        24px
        0;
}}

.figure img {{
    display: block;

    max-width: 100%;

    height: auto;

    margin: 0 auto;

    border:
        1px solid var(--border);

    border-radius: 6px;
}}

.figure-caption {{
    text-align: center;

    color: var(--muted);

    font-size: 14px;

    margin-top: 8px;
}}

table {{
    width: 100%;

    border-collapse: collapse;

    margin-top: 12px;
}}

th,
td {{
    text-align: left;

    vertical-align: top;

    padding: 10px;

    border-bottom:
        1px solid var(--border);
}}

th {{
    background: #f0f3f7;

    font-weight: 600;
}}

code {{
    font-family: monospace;

    font-size: 0.9em;
}}

.status {{
    display: inline-block;

    padding:
        3px
        8px;

    border-radius: 999px;

    font-size: 12px;

    font-weight: 700;
}}

.status.pass {{
    background: #e5f4ea;
    color: var(--pass);
}}

.status.info {{
    background: #e7f0fa;
    color: var(--info);
}}

.status.warning {{
    background: #fff0dc;
    color: var(--warning);
}}

.status.fail {{
    background: #fae5e5;
    color: var(--fail);
}}

.status.unknown {{
    background: #eeeeee;
    color: #555555;
}}

details {{
    margin-top: 6px;
}}

summary {{
    cursor: pointer;

    color: var(--muted);
}}

pre {{
    white-space: pre-wrap;

    word-break: break-word;

    background: #f4f6f8;

    padding: 12px;

    border-radius: 6px;

    overflow-x: auto;
}}

.limitation {{
    border-left:
        4px solid var(--warning);

    padding:
        12px
        16px;

    background: #fff8ee;

    margin-top: 12px;
}}

@media (max-width: 800px) {{

    .summary {{
        grid-template-columns:
            repeat(2, 1fr);
    }}

    table {{
        display: block;

        overflow-x: auto;
    }}

}}

</style>

</head>


<body>

<main>

<!-- ==================================== Titel og Undertitel ==================================== -->

<h1>QA Report</h1>

<p class="subtitle">Reproducerbar kvalitetskontrol af Danmarks Dybde Model (DDM)</p>



<!-- ==================================== Inputvalidering hurtig oversigt ==================================== -->

<section class="summary">

    <div class="summary-card pass">

        <div class="number">{summary["PASS"]}</div>

        <div class="label">PASS</div>

    </div>

    <div class="summary-card info">

        <div class="number">{summary["INFO"]}</div>

        <div class="label">INFO</div>

    </div>


    <div class="summary-card warning">

        <div class="number">{summary["WARNING"]}</div>

        <div class="label">WARNING</div>

    </div>

    <div class="summary-card fail">

        <div class="number">{summary["FAIL"]}</div>

        <div class="label">FAIL</div>
    
    </div>

</section>

<!-- ==================================== raster output  ==================================== -->

<section class="section">

    <h2>Lokal Variation</h2>

    <p>
       Analyse af lokale dybdeforskelle baseret på variation mellem naboceller. 
       Pixels over den beregnede percentilgrænse markeres som potentielt interessante områder og grupperes efter valgt connectivity.
    </p>

    <div class="figure">

        <img
            src="{escape(high_variation_src)}"
        >

        <div class="figure-caption">
            Potentielt intressante områder er mærkeret med hver deres unikke farve.
        </div>

    </div>

    <table>

        <tr>
            <th>Parameter</th>
            <th>Værdi</th>
        </tr>

        <tr>

            <td>
                Gyldige lokal-range pixels
            </td>

            <td>
                {format_number(
                    statistics.get(
                        "valid_pixels"
                    ),
                    0
                )}
            </td>

        </tr>

        <tr>

            <td>
                {percentile_label} tærskel
            </td>

            <td>
                {format_number(threshold)}
            </td>

        </tr>

        <tr>

            <td>
                Pixels med høj lokal variation
            </td>

            <td>
                {format_number(
                    analysis.get(
                        "variation_mask_pixels"
                    ),
                    0
                )}
            </td>

        </tr>


        <tr>

            <td>
                Sammenhængende områder
            </td>

            <td>
                {format_number(
                    areas.get(
                        "count"
                    ),
                    0
                )}
            </td>

        </tr>


        <tr>

            <td>
                Connectivity
            </td>

            <td>
                {escape(
                    areas.get(
                        "connectivity",
                        "—"
                    )
                )}
            </td>

        </tr>

    </table>


    <div class="limitation">

        <strong>Fortolkning:</strong>

        Høj lokal variation er et screeningssignal og er ikke i sig selv
        dokumentation for en fejl i DDM dataen

    </div>

</section>



<!-- ==================================== Overstigt over observationer  ==================================== -->

<section class="section">

<h2>QA-observationer</h2>

    <table>

        <thead>

            <tr>
                <th>Kode</th>
                <th>Status</th>
                <th>Observation</th>
                <th>Værdi</th>
                <th>Detaljer</th>
            </tr>

        </thead>

        <tbody>

            {render_observations(observations)}

        </tbody>

    </table>

</section>



<!-- ==================================== fordeling af datakilder Søjlediagram ==================================== -->

<section class="section">

    <h2>Datakilder</h2>

    <div class="figure">

        <img
            src="{escape(source_src)}"
            alt="Graf over fordeling af datakilder"
        >

        <div class="figure-caption">
            Fordeling af kildekoder blandt gyldige kildepixels.
        </div>

    </div>


    <table>

        <thead>

            <tr>
                <th>Kildekode</th>
                <th>Pixels</th>
                <th>Andel</th>
            </tr>

        </thead>

        <tbody>
            {render_source_distribution(input_inspection)}
        </tbody>

    </table>

</section>



<!-- ==================================== Datakomplethed Søjlediagram ==================================== -->

<section class="section">

    <h2>Datakomplethed</h2>

    <div class="figure">

        <img
            src="{escape(completeness_src)}"
            alt="Graf over datakomplethed"
        >

        <div class="figure-caption">
            Datakomplethed for de tre inputrasters.
        </div>

    </div>

    <table>

        <thead>

            <tr>
                <th>Raster</th>
                <th>Total pixels</th>
                <th>Gyldige pixels</th>
                <th>NoData pixels</th>
                <th>Gyldig data</th>
            </tr>

        </thead>

        <tbody>
            {render_completeness_table(input_inspection)}
        </tbody>

    </table>

</section>



<!-- ==================================== Overstigt over metadata  ==================================== -->

<section class="section">

    <h2>Metadata</h2>

    <table>

        <thead>

            <tr>
                <th>Raster</th>
                <th>Format</th>
                <th>Datatype</th>
                <th>CRS</th>
                <th>Beskrivelse</th>
                <th>Enhed</th>
                <th>Software</th>
                <th>Dato</th>
            </tr>

        </thead>

        <tbody>

            {render_metadata_table(metadata)}

        </tbody>

    </table>

</section>



<!-- ==================================== Rasteroutput oversig  ==================================== -->

<section class="section">

    <h2>Producerede Outputs</h2>

    <table>

        <thead>

            <tr>
                <th>Output</th>
                <th>Fil</th>
                <th>Resultat</th>
            </tr>

        </thead>

        <tbody>

        {render_outputs(outputs)}

        </tbody>

    </table>

</section>



<!-- ==================================== Afslutende bemærkning  ==================================== -->

<section class="section">

<section class="section">

    <h2>QA Forbehold</h2>

    <p>
        QA-workflowet gennemfører tekniske kontroller af datakomplethed,
        kilde- og årssammenhænge samt identificerer områder med høj
        lokal variation. Resultaterne skal anvendes som screeningsgrundlag
        for videre undersøgelse af Danmarks Dybde Model (DDM).
    </p>

    <ul>

        <li>
            Høj lokal variation afhænger af den valgte percentilgrænse
            og skal derfor fortolkes relativt til det analyserede datasæt.
        </li>

        <li>
            Måleusikkerhed og kvaliteten af den underliggende opmåling
            kan ikke bestemmes pålideligt ud fra dybderasteren alene.
        </li>

        <li>
            Manglende kildeår registreres som et QA-signal, men årsagen
            til manglen skal undersøges i den oprindelige datadokumentation.
        </li>

    </ul>

</section>

</main>

</body>

</html>
"""


def generate_report(results: dict, report_path: Path, figure_dir: Path, local_range_path: Path, pl_variation_areas_path: Path) -> dict:

    report_path = Path(report_path)
    figure_dir = Path(figure_dir)
    local_range_path = Path(local_range_path)
    pl_variation_areas_path = Path(
        pl_variation_areas_path
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    figure_paths = create_figures(
        results=results,
        figure_dir=figure_dir,
        local_range_path=local_range_path,
        pl_variation_areas_path=(
            pl_variation_areas_path
        ),
    )

    report = render_report(
        results=results,
        figure_paths=figure_paths,
    )

    report_path.write_text(
        report,
        encoding="utf-8",
    )

    return {
        "report": report_path,
        "figures": figure_paths,
    }