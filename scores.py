"""Merge final human scores with the response analysis and summarize the results."""

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
HAND_SCORES_PATH = BASE_DIR / "hand_scores.csv"
RESULTS_PATH = BASE_DIR / "results.csv"
FINAL_RESULTS_PATH = BASE_DIR / "final_results.csv"
WORDINGS = ["Plain", "Device named"]
COLORS = ["#6b6b6b", "#1f5fbf"]
PROBLEM_ORDER = [2, 4, 3, 1, 6, 5, 7, 8, 9]
CHART_SIZE = (12, 7)
RUN_COLUMNS = [
    ("Plain", 1),
    ("Plain", 2),
    ("Plain", 3),
    ("Device named", 1),
    ("Device named", 2),
    ("Device named", 3),
]

# Map the spreadsheet's human-readable column names to convenient Python names.
HAND_COLUMN_NAMES = {
    "#": "statement",
    "Problem": "hand_problem",
    "Wording": "wording",
    "Run": "run",
    "Causes hit": "causes_hit",
    "Causes total": "causes_total",
    "Solutions hit": "solutions_hit",
    "Solutions total": "solutions_total",
    "Wrong device?": "wrong_device",
    "Assumed unstated equipment?": "assumed_equipment",
    "Marketing / boilerplate?": "marketing_boilerplate",
    "Refers to provider?": "refers_to_provider",
    "Source cited": "hand_source_cited",
    "Notes": "notes",
}
KEY_COLUMNS = ["statement", "wording", "run"]
YES_NO_COLUMNS = [
    "wrong_device",
    "assumed_equipment",
    "marketing_boilerplate",
    "refers_to_provider",
]


def _read_hand_scores() -> pd.DataFrame:
    """Load the spreadsheet export, normalize its fields, and check its 54 rows."""
    if not HAND_SCORES_PATH.is_file():
        raise FileNotFoundError(
            f"Could not find hand scores: {HAND_SCORES_PATH}. "
            "Place hand_scores.csv in the project folder and rerun."
        )

    hand_scores = pd.read_csv(HAND_SCORES_PATH, dtype=str, keep_default_na=False)
    # Spreadsheet exports may add spaces around headers; trim them before matching.
    hand_scores.columns = [str(column).strip() for column in hand_scores.columns]
    missing_columns = set(HAND_COLUMN_NAMES) - set(hand_scores.columns)
    if missing_columns:
        raise ValueError(
            "hand_scores.csv is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    # Keep only the columns needed for this analysis and give them stable names.
    hand_scores = hand_scores[list(HAND_COLUMN_NAMES)].rename(
        columns=HAND_COLUMN_NAMES
    )
    for column in ["wording", "hand_problem", "hand_source_cited", "notes"]:
        hand_scores[column] = hand_scores[column].str.strip()
    for column in YES_NO_COLUMNS:
        hand_scores[column] = hand_scores[column].str.strip().str.upper()
        invalid_values = sorted(set(hand_scores[column]) - {"Y", "N"})
        if invalid_values:
            raise ValueError(
                f"Column {column!r} contains values other than Y/N: {invalid_values}"
            )

    # Convert the identifiers and score counts to numbers, rejecting malformed cells.
    numeric_columns = [
        "statement",
        "run",
        "causes_hit",
        "causes_total",
        "solutions_hit",
        "solutions_total",
    ]
    for column in numeric_columns:
        hand_scores[column] = pd.to_numeric(
            hand_scores[column], errors="raise"
        ).astype(int)

    if len(hand_scores) != 54:
        raise ValueError(f"Expected 54 hand-score rows, found {len(hand_scores)}")
    wording_counts = hand_scores["wording"].value_counts().to_dict()
    if wording_counts != {"Plain": 27, "Device named": 27}:
        raise ValueError(
            "Expected 27 rows for each wording (Plain and Device named); "
            f"found {wording_counts}"
        )
    if set(hand_scores["statement"]) != set(range(1, 10)):
        raise ValueError("Hand scores must cover statements 1 through 9")
    if set(hand_scores["run"]) != {1, 2, 3}:
        raise ValueError("Hand scores must cover runs 1 through 3")
    if hand_scores.duplicated(KEY_COLUMNS).any():
        raise ValueError("hand_scores.csv contains duplicate statement/wording/run keys")

    # A hit count cannot be negative or exceed the corresponding checklist total.
    for hits_column, total_column in [
        ("causes_hit", "causes_total"),
        ("solutions_hit", "solutions_total"),
    ]:
        invalid_scores = (
            (hand_scores[hits_column] < 0)
            | (hand_scores[total_column] < 0)
            | (hand_scores[hits_column] > hand_scores[total_column])
        )
        if invalid_scores.any():
            raise ValueError(
                f"Invalid hit/total values in {hits_column} and {total_column}"
            )
    if ((hand_scores["causes_total"] + hand_scores["solutions_total"]) <= 0).any():
        raise ValueError("Each response must have a positive combined manual total")
    return hand_scores


def merge_scores() -> pd.DataFrame:
    """Join the two files and calculate coverage and the combined issue flag."""
    hand_scores = _read_hand_scores()
    if not RESULTS_PATH.is_file():
        raise FileNotFoundError(f"Could not find analysis results: {RESULTS_PATH}")
    results = pd.read_csv(RESULTS_PATH, keep_default_na=False)
    results["statement"] = pd.to_numeric(results["statement"], errors="raise").astype(int)
    results["run"] = pd.to_numeric(results["run"], errors="raise").astype(int)
    if results.duplicated(KEY_COLUMNS).any():
        raise ValueError("results.csv contains duplicate statement/wording/run keys")

    # An outer join exposes missing keys on either side instead of silently dropping them.
    merged = hand_scores.merge(
        results,
        on=KEY_COLUMNS,
        how="outer",
        validate="one_to_one",
        indicator=True,
        suffixes=("_hand", "_analysis"),
    )
    unmatched = merged["_merge"] != "both"
    if unmatched.any() or len(merged) != 54:
        examples = merged.loc[unmatched, KEY_COLUMNS + ["_merge"]].head().to_dict("records")
        raise ValueError(
            f"Expected all 54 hand-score rows to match results.csv; "
            f"found {int((~unmatched).sum())} matched. Examples: {examples}"
        )
    merged = merged.drop(columns="_merge")

    # Coverage combines the manual's cause and solution checks for each response.
    total_hits = merged["causes_hit"] + merged["solutions_hit"]
    total_items = merged["causes_total"] + merged["solutions_total"]
    merged["coverage"] = total_hits / total_items

    # Mark a response as an issue if either of the two human-scored risk flags is Y.
    merged["any_issue"] = (
        (merged["wrong_device"] == "Y") | (merged["assumed_equipment"] == "Y")
    ).map({True: "Y", False: "N"})

    # The charts say "out of 3", so verify every statement/wording has three runs.
    run_counts = merged.groupby(["statement", "wording"]).size()
    if len(run_counts) != 18 or not (run_counts == 3).all():
        raise ValueError("Expected three runs for each statement and wording")
    return merged


def _add_bar_labels(axis: plt.Axes, percent: bool = False) -> None:
    """Write a value beside every bar so the chart is readable without estimating."""
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


def _save_grouped_chart(
    values: pd.DataFrame,
    title: str,
    xlabel: str,
    filename: str,
    *,
    percent: bool = False,
    divider_after: Optional[int] = None,
    caption: str = "n = 3 runs per wording per problem",
) -> None:
    """Save a horizontal grouped bar chart with the two wording types side by side."""
    figure, axis = plt.subplots(figsize=CHART_SIZE)
    axis = values.reindex(columns=WORDINGS, fill_value=0).plot(
        kind="barh",
        ax=axis,
        color=COLORS,
        width=0.8,
        legend=False,
    )
    axis.set_title(title, fontsize=16, pad=14)
    axis.set_xlabel(xlabel, fontsize=12)
    axis.set_ylabel("")
    axis.invert_yaxis()
    axis.tick_params(axis="both", labelsize=11)
    axis.grid(axis="x", linestyle=":", alpha=0.5)
    axis.set_axisbelow(True)
    maximum = values.to_numpy().max() if not values.empty else 0
    axis.set_xlim(0, max(145 if percent else 1, maximum * 1.35))
    _add_bar_labels(axis, percent=percent)
    if divider_after is not None:
        axis.axhline(divider_after + 0.5, color="#bdbdbd", linewidth=1)
    figure.text(0.30, 0.035, caption, ha="left", va="bottom", fontsize=10)
    figure.subplots_adjust(left=0.30, right=0.90, top=0.86, bottom=0.15)
    figure.savefig(BASE_DIR / filename, dpi=200)
    plt.close(figure)


def save_charts(merged: pd.DataFrame) -> None:
    """Build the three requested charts using the short problem names."""
    # Make a statement-to-short-name lookup and keep statements in numerical order.
    problem_names = (
        merged[["statement", "hand_problem"]]
        .drop_duplicates()
        .sort_values("statement")
        .set_index("statement")["hand_problem"]
    )
    if problem_names.index.duplicated().any():
        raise ValueError("Each statement must have one consistent short problem name")
    # Average the three individual response coverage scores for each problem/wording.
    coverage = merged.pivot_table(
        index="statement", columns="wording", values="coverage", aggfunc="mean"
    ).reindex(PROBLEM_ORDER)
    coverage.index = [problem_names.loc[number] for number in PROBLEM_ORDER]
    _save_grouped_chart(
        coverage * 100,
        "Naming the device helped most on device-specific problems",
        "Average coverage (%)",
        "coverage_by_statement.png",
        percent=True,
        divider_after=4,
    )

    # Count responses flagged for wrong device or unstated equipment, out of three.
    issue_counts = merged.assign(
        issue_count=(merged["any_issue"] == "Y").astype(int)
    ).pivot_table(
        index="statement",
        columns="wording",
        values="issue_count",
        aggfunc="sum",
        fill_value=0,
    ).reindex(PROBLEM_ORDER)
    issue_counts.index = [problem_names.loc[number] for number in PROBLEM_ORDER]
    _save_grouped_chart(
        issue_counts,
        "Responses with an issue by problem",
        "Responses with issue (out of 3)",
        "issues_by_statement.png",
        divider_after=4,
    )

    # Compare total risk and marketing flags by wording across all 27 responses.
    issue_type_counts = pd.DataFrame(
        {
            "Wrong device": [
                (merged.loc[merged["wording"] == wording, "wrong_device"] == "Y").sum()
                for wording in WORDINGS
            ],
            "Assumed equipment": [
                (merged.loc[merged["wording"] == wording, "assumed_equipment"] == "Y").sum()
                for wording in WORDINGS
            ],
            "Marketing / boilerplate": [
                (merged.loc[merged["wording"] == wording, "marketing_boilerplate"] == "Y").sum()
                for wording in WORDINGS
            ],
        },
        index=WORDINGS,
    ).T
    _save_grouped_chart(
        issue_type_counts,
        "Issue and marketing counts by wording",
        "Responses (out of 27)",
        "issue_types_by_wording.png",
        caption="n = 27 responses per wording",
    )
    _save_coverage_dumbbell(merged, problem_names)
    _save_runs_grid(merged, problem_names)


def _save_coverage_dumbbell(
    merged: pd.DataFrame, problem_names: pd.Series
) -> None:
    """Compare mean coverage directly with paired dots, labels, and group headings."""
    coverage = merged.pivot_table(
        index="statement", columns="wording", values="coverage", aggfunc="mean"
    ).reindex(PROBLEM_ORDER)
    figure, axis = plt.subplots(figsize=CHART_SIZE)
    row_positions = [0, 1, 2, 3, 4, 5.5, 6.5, 7.5, 8.5]
    for row_index, statement in enumerate(PROBLEM_ORDER):
        y_position = row_positions[row_index]
        plain_value = float(coverage.loc[statement, "Plain"] * 100)
        named_value = float(coverage.loc[statement, "Device named"] * 100)
        axis.plot(
            [plain_value, named_value],
            [y_position, y_position],
            color="#bdbdbd",
            linewidth=1.5,
            zorder=1,
        )
        for wording, value, color, y_offset in [
            ("Plain", plain_value, COLORS[0], -0.10),
            ("Device named", named_value, COLORS[1], 0.10),
        ]:
            axis.scatter(
                value,
                y_position + y_offset,
                color=color,
                s=85,
                zorder=2,
            )
            axis.annotate(
                f"{value:.0f}% {wording}",
                (value, y_position + y_offset),
                xytext=(7, 0),
                textcoords="offset points",
                va="center",
                fontsize=9,
                color=color,
                fontweight="bold",
            )

    axis.set_yticks(
        row_positions,
        [problem_names.loc[number] for number in PROBLEM_ORDER],
    )
    axis.set_xlim(0, 125)
    axis.set_xticks(range(0, 101, 20), [f"{value}%" for value in range(0, 101, 20)])
    axis.set_ylim(9.2, -0.8)
    axis.set_xlabel("Average manual coverage", fontsize=12)
    axis.set_title(
        "Naming the device helped most on device-specific problems",
        fontsize=16,
        pad=14,
    )
    axis.tick_params(axis="both", labelsize=10)
    axis.grid(axis="x", linestyle=":", alpha=0.5)
    axis.set_axisbelow(True)
    axis.axhline(4.75, color="#bdbdbd", linewidth=1)
    axis.text(
        50,
        -0.48,
        "GENERAL COMFORT",
        ha="center",
        va="center",
        fontsize=9,
        color="#555555",
        fontweight="bold",
    )
    axis.text(
        50,
        5.02,
        "DEVICE-SPECIFIC",
        ha="center",
        va="center",
        fontsize=9,
        color="#555555",
        fontweight="bold",
    )
    figure.text(
        0.30,
        0.035,
        "n = 3 runs per wording per problem. Coverage = share of the manual's causes and solutions mentioned.",
        ha="left",
        va="bottom",
        fontsize=9,
    )
    figure.subplots_adjust(left=0.30, right=0.94, top=0.86, bottom=0.15)
    figure.savefig(BASE_DIR / "coverage_dumbbell.png", dpi=200)
    plt.close(figure)


def _save_runs_grid(merged: pd.DataFrame, problem_names: pd.Series) -> None:
    """Display every response's coverage in a heatmap grid and flag issue rows."""
    ordered = merged.copy()
    ordered["statement"] = pd.Categorical(
        ordered["statement"], categories=PROBLEM_ORDER, ordered=True
    )
    ordered["wording"] = pd.Categorical(
        ordered["wording"], categories=WORDINGS, ordered=True
    )
    ordered = ordered.sort_values(["statement", "wording", "run"])
    coverage_values = ordered["coverage"].to_numpy().reshape(9, 6)
    issues = (ordered["any_issue"] == "Y").to_numpy().reshape(9, 6)

    figure, axis = plt.subplots(figsize=CHART_SIZE)
    color_map = plt.get_cmap("Blues")
    for row_index in range(9):
        for column_index in range(6):
            value = float(coverage_values[row_index, column_index])
            color = color_map(0.15 + value * 0.75)
            axis.add_patch(
                Rectangle(
                    (column_index - 0.48, row_index - 0.46),
                    0.96,
                    0.92,
                    facecolor=color,
                    edgecolor="white",
                    linewidth=1,
                )
            )
            text_color = "white" if value >= 0.65 else "#111111"
            axis.text(
                column_index,
                row_index,
                f"{value * 100:.0f}%",
                ha="center",
                va="center",
                fontsize=11,
                color=text_color,
                fontweight="bold",
            )
            if issues[row_index, column_index]:
                axis.text(
                    column_index + 0.36,
                    row_index - 0.33,
                    "!",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="black",
                    fontweight="bold",
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5},
                )

    axis.set_xlim(-1.65, 5.55)
    axis.set_ylim(8.55, -1.45)
    axis.set_xticks(range(6), ["1", "2", "3", "1", "2", "3"])
    axis.xaxis.tick_top()
    axis.tick_params(axis="x", labelsize=11, length=0, pad=5)
    axis.set_yticks(
        range(9),
        [problem_names.loc[number] for number in PROBLEM_ORDER],
    )
    axis.tick_params(axis="y", labelsize=10, length=0)
    axis.text(1, -1.12, "PLAIN", ha="center", va="center", fontsize=11, fontweight="bold", color=COLORS[0])
    axis.text(4, -1.12, "DEVICE NAMED", ha="center", va="center", fontsize=11, fontweight="bold", color=COLORS[1])
    axis.axvline(2.5, color="#777777", linewidth=1)
    axis.axhline(4.5, color="#bdbdbd", linewidth=1)
    axis.set_title("Coverage and issues for every run", fontsize=16, pad=50)
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.text(
        0.30,
        0.035,
        "Each cell is one Dawn response. ! = wrong device or assumed mask.",
        ha="left",
        va="bottom",
        fontsize=10,
    )
    figure.subplots_adjust(left=0.30, right=0.94, top=0.79, bottom=0.15)
    figure.savefig(BASE_DIR / "runs_grid.png", dpi=200)
    plt.close(figure)


def main() -> None:
    """Save the merged results, print summaries, and create the charts."""
    merged = merge_scores()
    merged.to_csv(FINAL_RESULTS_PATH, index=False)

    # Show the average coverage and number of Y ratings for each wording.
    summary = merged.groupby("wording").agg(
        average_coverage=("coverage", "mean"),
        wrong_device=("wrong_device", lambda values: (values == "Y").sum()),
        assumed_equipment=("assumed_equipment", lambda values: (values == "Y").sum()),
        any_issue=("any_issue", lambda values: (values == "Y").sum()),
        marketing_boilerplate=(
            "marketing_boilerplate",
            lambda values: (values == "Y").sum(),
        ),
        refers_to_provider=(
            "refers_to_provider",
            lambda values: (values == "Y").sum(),
        ),
    ).reindex(WORDINGS)
    summary["average_coverage"] *= 100
    print("\nSummary by wording (coverage as a percentage):")
    print(summary.round({"average_coverage": 1}).to_string())

    # Pivot tables make it easy to compare the two wordings statement by statement.
    coverage_by_statement = merged.pivot_table(
        index="statement", columns="wording", values="coverage", aggfunc="mean"
    ) * 100
    print("\nAverage coverage by statement and wording (%):")
    print(coverage_by_statement.round(1).reindex(range(1, 10)).to_string())

    issue_by_statement = merged.assign(
        issue_count=(merged["any_issue"] == "Y").astype(int)
    ).pivot_table(
        index="statement",
        columns="wording",
        values="issue_count",
        aggfunc="sum",
        fill_value=0,
    )
    print("\nAny issue by statement and wording (out of 3):")
    print(issue_by_statement.reindex(range(1, 10), fill_value=0).to_string())

    save_charts(merged)
    print(f"\nSaved {len(merged)} merged rows to {FINAL_RESULTS_PATH.name}")
    print("Saved coverage_by_statement.png, issues_by_statement.png, and issue_types_by_wording.png")


if __name__ == "__main__":
    main()
