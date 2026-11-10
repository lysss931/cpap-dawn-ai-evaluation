"""Create grouped horizontal bar charts from the analyzed response data."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "results.csv"
WORDINGS = ["Plain", "Device named"]
COLORS = ["#4C78A8", "#F58518"]


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
    figsize: tuple[float, float] = (10, 6),
) -> None:
    """Draw and save a horizontal grouped bar chart with a consistent wording legend."""
    axis = data.reindex(columns=WORDINGS, fill_value=0).plot(
        kind="barh",
        figsize=figsize,
        color=COLORS,
        width=0.8,
    )
    axis.set_title(title)
    axis.set_xlabel(xlabel)
    axis.set_ylabel("")
    axis.invert_yaxis()
    axis.legend(title="Wording")
    axis.grid(axis="x", linestyle=":", alpha=0.5)
    axis.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(BASE_DIR / filename, dpi=160)
    plt.close()


def main() -> None:
    """Generate the four requested grouped bar charts."""
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Could not find analyzed data: {INPUT_PATH}")
    results = pd.read_csv(INPUT_PATH, keep_default_na=False)
    results["statement"] = results["statement"].astype(int)

    # Compare average response lengths after removing the marketing boilerplate.
    words = results.pivot_table(
        index="statement", columns="wording", values="words_no_boilerplate", aggfunc="mean"
    )
    save_grouped_bar(
        words,
        "Average words per response (boilerplate removed)",
        "Average words",
        "average_words_by_statement.png",
    )

    # Convert the match ratio to a percentage for an easier visual comparison.
    match = results.pivot_table(
        index="statement", columns="wording", values="key_term_match", aggfunc="mean"
    ) * 100
    save_grouped_bar(
        match,
        "Key-term match by statement",
        "Key terms matched (%)",
        "key_term_match_by_statement.png",
    )

    # Normalize filenames so different AirFit models share the same chart category.
    results["document_category"] = results["source_cited"].map(document_category)
    document_counts = results.pivot_table(
        index="document_category",
        columns="wording",
        values="statement",
        aggfunc="count",
        fill_value=0,
    ).reindex(
        ["AirSense 11 manual", "AirSense 10 manual", "AirFit mask guide", "None"],
        fill_value=0,
    )
    save_grouped_bar(
        document_counts,
        "Which document Dawn linked",
        "Number of responses",
        "document_links_by_wording.png",
        figsize=(10, 5),
    )

    # Sum the Y/N flag to show boilerplate response counts out of three runs.
    boilerplate = results.assign(
        boilerplate_count=(results["has_boilerplate"] == "Y").astype(int)
    ).pivot_table(
        index="statement",
        columns="wording",
        values="boilerplate_count",
        aggfunc="sum",
        fill_value=0,
    )
    save_grouped_bar(
        boilerplate,
        "Responses with marketing boilerplate",
        "Responses (out of 3)",
        "boilerplate_by_statement.png",
    )
    print("Saved four charts in the project folder.")


if __name__ == "__main__":
    main()
