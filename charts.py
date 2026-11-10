"""Create grouped horizontal bar charts from the analyzed response data."""

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "results.csv"
WORDINGS = ["Plain", "Device named"]
COLORS = ["#6b6b6b", "#1f5fbf"]
DOCUMENTS = [
    "AirSense 11 manual",
    "AirSense 10 manual",
    "AirFit mask guide",
    "None",
]
DOCUMENT_COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
PROBLEM_NAMES = {
    1: "Mask leak",
    2: "Dry/blocked nose",
    3: "Water droplets",
    4: "Dry mouth",
    5: "Black screen",
    6: "Humidifier tub leak",
    7: "Data not sent",
    8: "SmartStart not starting",
    9: "SmartStop not stopping",
}
PROBLEM_ORDER = [2, 4, 3, 1, 6, 5, 7, 8, 9]
CHART_SIZE = (12, 7)


def document_category(source: str) -> str:
    """Group linked PDF filenames into the four document categories in the brief."""
    source_name = source.casefold()
    if not source:
        return "None"
    if "airfit" in source_name:
        return "AirFit mask guide"
    if "airsense_10" in source_name or "airsense 10" in source_name:
        return "AirSense 10 manual"
    if "airsense_11" in source_name or "airsense 11" in source_name:
        return "AirSense 11 manual"
    raise ValueError(f"Unrecognized cited document: {source}")


def save_grouped_bar(
    data: pd.DataFrame,
    title: str,
    xlabel: str,
    filename: str,
    *,
    percent: bool = False,
    divider_after: Optional[int] = None,
    caption: str = "n = 3 runs per wording per problem",
) -> None:
    """Draw a labeled, consistently styled chart and save it at webpage-friendly resolution."""
    figure, axis = plt.subplots(figsize=CHART_SIZE)
    data.reindex(columns=WORDINGS, fill_value=0).plot(
        kind="barh",
        color=COLORS,
        width=0.8,
        ax=axis,
        legend=False,
    )
    axis.set_title(title, fontsize=16, pad=14)
    axis.set_xlabel(xlabel, fontsize=12)
    axis.set_ylabel("")
    axis.invert_yaxis()
    axis.tick_params(axis="both", labelsize=11)
    axis.grid(axis="x", linestyle=":", alpha=0.5)
    axis.set_axisbelow(True)

    # Leave room at the right for the legend, at the left for problem names,
    # and below the plot for the sample-size caption.
    maximum = data.to_numpy().max() if not data.empty else 0
    axis.set_xlim(0, max(145 if percent else 1, maximum * 1.35))
    for series_index, bars in enumerate(axis.containers):
        for bar in bars:
            value = bar.get_width()
            wording = WORDINGS[series_index]
            label = f"{value:.0f}% {wording}" if percent else f"{value:.0f} {wording}"
            axis.annotate(
                label,
                (value, bar.get_y() + bar.get_height() / 2),
                xytext=(4, 0),
                textcoords="offset points",
                va="center",
                fontsize=10,
            )
    if divider_after is not None:
        axis.axhline(divider_after + 0.5, color="#bdbdbd", linewidth=1)
    figure.text(0.30, 0.035, caption, ha="left", va="bottom", fontsize=10)
    figure.subplots_adjust(left=0.30, right=0.78, top=0.86, bottom=0.15)
    figure.savefig(BASE_DIR / filename, dpi=200)
    plt.close(figure)


def save_document_links_stacked(results: pd.DataFrame) -> None:
    """Create the 100% stacked chart and show each document count in its segment."""
    counts = results.pivot_table(
        index="wording",
        columns="document_category",
        values="statement",
        aggfunc="count",
        fill_value=0,
    ).reindex(index=WORDINGS, columns=DOCUMENTS, fill_value=0)
    shares = counts.div(counts.sum(axis=1), axis=0)

    figure, axis = plt.subplots(figsize=CHART_SIZE)
    vertical_positions = [1, 0]
    height = 0.55
    for row_index, wording in enumerate(WORDINGS):
        y_position = vertical_positions[row_index]
        left = 0.0
        for document, color in zip(DOCUMENTS, DOCUMENT_COLORS):
            share = float(shares.loc[wording, document])
            count = int(counts.loc[wording, document])
            axis.barh(
                y_position,
                share * 100,
                left=left * 100,
                height=height,
                color=color,
                edgecolor="white",
                linewidth=1,
            )
            if count:
                text_color = "white" if document == "AirSense 11 manual" else "black"
                axis.text(
                    (left + share / 2) * 100,
                    y_position,
                    str(count),
                    ha="center",
                    va="center",
                    color=text_color,
                    fontsize=12,
                    fontweight="bold",
                )
            else:
                # Keep zero-count categories visible at their boundary without
                # pretending they occupy space in the 100% bar.
                axis.annotate(
                    "0",
                    (left * 100, y_position),
                    xytext=(0, -23 if row_index == 0 else 23),
                    textcoords="offset points",
                    ha="center",
                    va="center",
                    fontsize=10,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 1},
                )
            left += share

    axis.set_yticks(vertical_positions, WORDINGS)
    axis.set_xlim(0, 100)
    axis.set_xticks(range(0, 101, 20), [f"{value}%" for value in range(0, 101, 20)])
    axis.set_xlabel("Share of responses", fontsize=12)
    axis.set_title(
        "Dawn linked the AirSense 11 manual only when the device was named",
        fontsize=16,
        pad=14,
    )
    axis.tick_params(axis="both", labelsize=11)
    axis.grid(axis="x", linestyle=":", alpha=0.5)
    axis.set_axisbelow(True)
    axis.legend(
        handles=[
            Patch(facecolor=color, label=document)
            for document, color in zip(DOCUMENTS, DOCUMENT_COLORS)
        ],
        title="Document",
        fontsize=10,
        title_fontsize=11,
        loc="upper left",
        bbox_to_anchor=(1.03, 1),
        frameon=False,
    )
    figure.text(
        0.30,
        0.035,
        "n = 27 responses per wording",
        ha="left",
        va="bottom",
        fontsize=10,
    )
    figure.subplots_adjust(left=0.30, right=0.76, top=0.84, bottom=0.18)
    figure.savefig(BASE_DIR / "document_links_stacked.png", dpi=200)
    plt.close(figure)


def main() -> None:
    """Generate the four requested grouped bar charts."""
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Could not find analyzed data: {INPUT_PATH}")
    results = pd.read_csv(INPUT_PATH, keep_default_na=False)
    results["statement"] = results["statement"].astype(int)

    # Compare average response lengths after removing the marketing boilerplate.
    words = results.pivot_table(
        index="statement", columns="wording", values="words_no_boilerplate", aggfunc="mean"
    ).reindex(PROBLEM_ORDER)
    words.index = [PROBLEM_NAMES[number] for number in PROBLEM_ORDER]
    save_grouped_bar(
        words,
        "Average words per response (boilerplate removed)",
        "Average words",
        "average_words_by_statement.png",
    )

    # Convert the match ratio to a percentage for an easier visual comparison.
    match = results.pivot_table(
        index="statement", columns="wording", values="key_term_match", aggfunc="mean"
    ).reindex(PROBLEM_ORDER) * 100
    match.index = [PROBLEM_NAMES[number] for number in PROBLEM_ORDER]
    save_grouped_bar(
        match,
        "Key-term match by statement",
        "Key terms matched (%)",
        "key_term_match_by_statement.png",
        percent=True,
    )

    # Normalize filenames so different AirFit models share the same chart category.
    results["document_category"] = results["source_cited"].map(document_category)
    document_counts = results.pivot_table(
        index="document_category",
        columns="wording",
        values="statement",
        aggfunc="count",
        fill_value=0,
    ).reindex(DOCUMENTS, fill_value=0)
    save_grouped_bar(
        document_counts,
        "Dawn linked the AirSense 11 manual only when the device was named",
        "Number of responses",
        "document_links_by_wording.png",
        caption="n = 27 responses per wording",
    )
    save_document_links_stacked(results)

    # Sum the Y/N flag to show boilerplate response counts out of three runs.
    boilerplate = results.assign(
        boilerplate_count=(results["has_boilerplate"] == "Y").astype(int)
    ).pivot_table(
        index="statement",
        columns="wording",
        values="boilerplate_count",
        aggfunc="sum",
        fill_value=0,
    ).reindex(PROBLEM_ORDER)
    boilerplate.index = [PROBLEM_NAMES[number] for number in PROBLEM_ORDER]
    save_grouped_bar(
        boilerplate,
        "Responses with marketing boilerplate",
        "Responses (out of 3)",
        "boilerplate_by_statement.png",
        divider_after=4,
    )
    print("Saved five charts in the project folder.")


if __name__ == "__main__":
    main()
