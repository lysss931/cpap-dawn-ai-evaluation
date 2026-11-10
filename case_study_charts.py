"""
Case study charts (reader-friendly versions)
--------------------------------------------
Makes five charts for the portfolio case study:
  From hand_scores.csv (my hand scores):  cs_coverage.png, cs_issues.png, cs_documents.png
  From results.csv (made by analyze.py):  cs_length.png, cs_keyterms.png

Design choices (human factors):
- Plain-language labels: "Problem only" vs. "Problem + device name"
- One message per chart; the title states the finding, the subtitle says what is measured
- Labels sit next to the data (no legend to look up)
- Color is never the only cue (shapes, positions and text carry the meaning too)
- Text and marks meet WCAG contrast guidance on a white background

Run with:  python case_study_charts.py
"""

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ---------- settings ----------
GRAY = "#5f5f5f"      # "Problem only"
BLUE = "#1f5fbf"      # "Problem + device name"
RED = "#c0392b"       # an issue
LIGHT = "#d9d9d9"     # empty / neutral
TEXT = "#222222"
SUB = "#555555"

COND_PLAIN, COND_DEVICE = "Plain", "Device named"
LABEL = {COND_PLAIN: "Problem only", COND_DEVICE: "Problem + device name"}

# Problems grouped: general comfort problems first, then device-specific features
GENERAL = ["Dry/blocked nose", "Dry mouth", "Water droplets", "Mask leak", "Humidifier tub leak"]
DEVICE = ["Black screen", "Data not sent", "SmartStart not starting", "SmartStop not stopping"]
ORDER = GENERAL + DEVICE

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12, "axes.edgecolor": "#bbbbbb"})


def load():
    df = pd.read_csv("hand_scores.csv")
    df.columns = [c.strip() for c in df.columns]
    df["coverage"] = (df["Causes hit"] + df["Solutions hit"]) / (df["Causes total"] + df["Solutions total"])
    df["issue"] = (df["Wrong device?"].str.strip() == "Y") | (df["Assumed unstated equipment?"].str.strip() == "Y")
    return df


def header(fig, title, subtitle):
    fig.text(0.03, 0.965, title, fontsize=17, fontweight="bold", color=TEXT, va="top")
    fig.text(0.03, 0.905, subtitle, fontsize=12, color=SUB, va="top")


def footer(fig, text):
    fig.text(0.03, 0.025, text, fontsize=10, color=SUB)


# ---------- shared dumbbell layout (charts 1, 4 and 5 use the same visual language) ----------
def dumbbell(avg, title, subtitle, foot, fname, xmax=100, ticks=(0, 25, 50, 75, 100), unit="%", same_tol=0.5):
    """avg: DataFrame indexed by Problem with columns COND_PLAIN and COND_DEVICE."""
    fmt = (lambda v: f"{v:.0f}%") if unit == "%" else (lambda v: f"{v:.0f}")
    pad = xmax * 0.03
    fig, ax = plt.subplots(figsize=(11, 7.2))
    fig.subplots_adjust(left=0.25, right=0.95, top=0.76, bottom=0.13)
    header(fig, title, subtitle)

    ys, y = {}, 0
    for p in ORDER:
        if p == DEVICE[0]:
            y += 1.0  # gap between the two groups
        ys[p] = y
        y += 1
    for p in ORDER:
        yy = -ys[p]
        a, b = avg.loc[p, COND_PLAIN], avg.loc[p, COND_DEVICE]
        ax.plot([a, b], [yy, yy], color="#c8c8c8", lw=3, zorder=1)
        if abs(a - b) < same_tol:
            ax.scatter([a], [yy], s=150, color="white", edgecolor=TEXT, lw=1.5, zorder=3)
            ax.text(a + pad, yy, f"{fmt(a)} both ways", va="center", fontsize=11, color=TEXT)
        else:
            ax.scatter([a], [yy], s=150, color=GRAY, zorder=3)
            ax.scatter([b], [yy], s=150, color=BLUE, zorder=3)
            lo, hi = (a, b) if a < b else (b, a)
            lo_c, hi_c = (GRAY, BLUE) if a < b else (BLUE, GRAY)
            if lo - xmax * 0.10 < 0:   # no room on the left: label sits above the dot
                ax.text(lo, yy + 0.38, fmt(lo), va="bottom", ha="center", fontsize=11, color=lo_c, fontweight="bold")
            else:
                ax.text(lo - pad, yy, fmt(lo), va="center", ha="right", fontsize=11, color=lo_c, fontweight="bold")
            ax.text(hi + pad, yy, fmt(hi), va="center", ha="left", fontsize=11, color=hi_c, fontweight="bold")

    ax.set_yticks([-ys[p] for p in ORDER])
    ax.set_yticklabels(ORDER, fontsize=12)
    ax.set_ylim(-ys[ORDER[-1]] - 0.6, 1.2)
    ax.set_xlim(-xmax * 0.05, xmax * 1.22)
    ax.set_xticks(list(ticks))
    ax.set_xticklabels([fmt(t) for t in ticks], color=SUB)
    ax.grid(axis="x", color="#eeeeee")
    for s_ in ["top", "right", "left"]:
        ax.spines[s_].set_visible(False)
    ax.tick_params(axis="y", length=0)

    ax.axhline(-ys[GENERAL[-1]] - 0.6, color="#bbbbbb", lw=1)
    ax.text(-xmax * 0.05, -ys[GENERAL[0]] + 0.75, "GENERAL COMFORT PROBLEMS", fontsize=10.5, color=SUB, fontweight="bold")
    ax.text(-xmax * 0.05, -ys[DEVICE[0]] + 0.75, "DEVICE-SPECIFIC FEATURES", fontsize=10.5, color=SUB, fontweight="bold")

    fig.text(0.25, 0.835, "●", color=GRAY, fontsize=16, va="center")
    fig.text(0.27, 0.835, "Problem only", color=GRAY, fontsize=12, va="center", fontweight="bold")
    fig.text(0.43, 0.835, "●", color=BLUE, fontsize=16, va="center")
    fig.text(0.45, 0.835, "Problem + device name", color=BLUE, fontsize=12, va="center", fontweight="bold")
    if any(abs(avg.loc[p, COND_PLAIN] - avg.loc[p, COND_DEVICE]) < same_tol for p in ORDER):
        fig.text(0.70, 0.835, "○", color=TEXT, fontsize=16, va="center")
        fig.text(0.72, 0.835, "Same both ways", color=TEXT, fontsize=12, va="center")

    footer(fig, foot)
    fig.savefig(fname, dpi=200)
    plt.close(fig)


# ---------- 1. Coverage (hand-scored) ----------
def coverage_chart(df):
    avg = df.groupby(["Problem", "Wording"])["coverage"].mean().unstack() * 100
    dumbbell(avg,
             "Naming the device helped most on device-specific problems",
             "How much of the manual's advice Dawn included (average of 3 tries per problem)",
             "100% = Dawn mentioned every cause and fix the AirSense 11 manual lists for that problem. "
             "3 tries per problem per wording.",
             "cs_coverage.png")


# ---------- 2. Issues: 3 tries shown as boxes ----------
def issues_chart(df):
    fig, ax = plt.subplots(figsize=(11, 7.2))
    fig.subplots_adjust(left=0.25, right=0.97, top=0.78, bottom=0.10)
    header(fig, "Without the device name, Dawn often answered for the wrong equipment",
           "Out of 3 tries, how many answers referred to the wrong device or assumed a mask the user never mentioned")

    ys, y = {}, 0
    for p in ORDER:
        if p == DEVICE[0]:
            y += 0.8
        ys[p] = y
        y += 1
    box, gap = 0.62, 0.15
    col_x = {COND_PLAIN: 0.0, COND_DEVICE: 4.2}
    for p in ORDER:
        yy = -ys[p]
        for cond in (COND_PLAIN, COND_DEVICE):
            runs = df[(df["Problem"] == p) & (df["Wording"] == cond)].sort_values("Run")
            n_issue = int(runs["issue"].sum())
            for k, has in enumerate(runs["issue"]):
                x = col_x[cond] + k * (box + gap)
                if has:
                    ax.add_patch(Rectangle((x, yy - box / 2), box, box, color=RED))
                    ax.text(x + box / 2, yy, "✕", ha="center", va="center", color="white", fontsize=12, fontweight="bold")
                else:
                    ax.add_patch(Rectangle((x, yy - box / 2), box, box, facecolor="white", edgecolor="#9a9a9a", lw=1.2))
            ax.text(col_x[cond] + 3 * (box + gap) + 0.1, yy, f"{n_issue} of 3", va="center", fontsize=11,
                    color=RED if n_issue else SUB, fontweight="bold" if n_issue else "normal")

    for cond in (COND_PLAIN, COND_DEVICE):
        ax.text(col_x[cond], 0.9, LABEL[cond], fontsize=12, fontweight="bold",
                color=GRAY if cond == COND_PLAIN else BLUE)
    mid = -(ys[GENERAL[-1]] + ys[DEVICE[0]]) / 2
    ax.axhline(mid, color="#999999", lw=1)
    ax.set_yticks([-ys[p] for p in ORDER])
    ax.set_yticklabels(ORDER, fontsize=12)
    ax.set_xlim(-0.3, 8.4)
    ax.set_ylim(-ys[ORDER[-1]] - 0.8, 1.5)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="y", length=0)

    # key
    fig.add_artist(Rectangle((0.25, 0.815), 0.015, 0.025, color=RED, transform=fig.transFigure))
    fig.text(0.27, 0.828, "Issue in that answer", fontsize=11, va="center", color=TEXT)
    fig.add_artist(Rectangle((0.45, 0.815), 0.015, 0.025, facecolor="white", edgecolor="#9a9a9a", transform=fig.transFigure))
    fig.text(0.47, 0.828, "No issue", fontsize=11, va="center", color=TEXT)
    footer(fig, "Each box is one Dawn answer. Examples of issues: instructions for the AirSense 10 or a control the\n"
                "AirSense 11 doesn't have; steps for an AirFit F20 mask.")
    fig.savefig("cs_issues.png", dpi=200)
    plt.close(fig)


# ---------- 3. Which document Dawn linked ----------
def documents_chart(df):
    def kind(s):
        s = str(s)
        if s == "Airsense_11.pdf":
            return "AirSense 11 manual (correct)"
        if s == "Airsense_10.pdf":
            return "AirSense 10 manual (wrong device)"
        if s.startswith("AirFit"):
            return "Mask guide (mask never mentioned)"
        return "No link"
    df = df.assign(doc=df["Source cited"].map(kind))
    cats = ["AirSense 11 manual (correct)", "AirSense 10 manual (wrong device)",
            "Mask guide (mask never mentioned)", "No link"]
    colors = {cats[0]: BLUE, cats[1]: "#b35900", cats[2]: "#e8a15c", cats[3]: LIGHT}
    text_on = {cats[0]: "white", cats[1]: "white", cats[2]: TEXT, cats[3]: TEXT}
    counts = df.groupby(["Wording", "doc"]).size().unstack(fill_value=0).reindex(columns=cats, fill_value=0)

    fig, ax = plt.subplots(figsize=(11, 5.6))
    fig.subplots_adjust(left=0.25, right=0.97, top=0.76, bottom=0.30)
    header(fig, "Dawn linked the AirSense 11 manual only when the device was named",
           "Which document Dawn's \"Learn More\" link pointed to (27 answers per wording)")
    rows = [COND_PLAIN, COND_DEVICE]
    for i, cond in enumerate(rows):
        left = 0
        y = 1 - i
        for c in cats:
            n = int(counts.loc[cond, c])
            if n == 0:
                continue
            ax.barh(y, n, left=left, color=colors[c], edgecolor="white", height=0.6)
            ax.text(left + n / 2, y, str(n), ha="center", va="center", fontsize=13, fontweight="bold", color=text_on[c])
            left += n
    ax.set_yticks([1, 0])
    ax.set_yticklabels([LABEL[r] for r in rows], fontsize=12)
    ax.set_xlim(0, 27)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis="y", length=0)

    # key below, in reading order, with plain-language meaning
    pos = [(0.25, 0.20), (0.25, 0.13), (0.60, 0.20), (0.60, 0.13)]
    for c, (x0, y0) in zip(cats, pos):
        fig.add_artist(Rectangle((x0, y0 - 0.02), 0.018, 0.04, color=colors[c], transform=fig.transFigure))
        fig.text(x0 + 0.026, y0, c, fontsize=11, va="center", color=TEXT)
    footer(fig, "Without the device name, 0 of 27 answers linked the AirSense 11 manual; with it, 16 of 27 did.")
    fig.savefig("cs_documents.png", dpi=200)
    plt.close(fig)


# ---------- Python text-analysis charts (read results.csv, made by analyze.py) ----------
def load_text_metrics(hand):
    r = pd.read_csv("results.csv")
    names = hand.drop_duplicates("#").set_index("#")["Problem"]
    r["Problem"] = r["statement"].map(names)
    r["Wording"] = r["wording"]
    return r


# ---------- 4. Answer length ----------
def length_chart(r):
    avg = r.groupby(["Problem", "Wording"])["words_no_boilerplate"].mean().unstack()
    n_promo = int((r["has_boilerplate"] == "Y").sum())
    dumbbell(avg,
             "Naming the device made every answer longer",
             "Average number of words in Dawn's answer (counted by Python). Longer doesn't mean more complete.",
             f"Not counted: a promotional sleep-assessment paragraph Dawn added to {n_promo} of {len(r)} answers.\n"
             "Example: SmartStop answers grew from 94 to 119 words, but manual coverage only went from 27% to 33%.",
             "cs_length.png", xmax=160, ticks=(0, 40, 80, 120, 160), unit="words", same_tol=0.5)


# ---------- 5. Key-term match ----------
def keyterm_chart(r):
    avg = r.groupby(["Problem", "Wording"])["key_term_match"].mean().unstack() * 100
    dumbbell(avg,
             "A Python keyword check mostly agreed with the hand scores",
             "Share of the manual's key terms (e.g., \"chin strap\", \"wireless coverage\") found in Dawn's answer",
             "Python searched each answer for the manual's key terms. It matches words, not meaning,\n"
             "so it supports the hand scores rather than replacing them.",
             "cs_keyterms.png")


if __name__ == "__main__":
    data = load()
    assert len(data) == 54, "Expected 54 responses in hand_scores.csv"
    coverage_chart(data)
    issues_chart(data)
    documents_chart(data)
    text = load_text_metrics(data)
    length_chart(text)
    keyterm_chart(text)
    print("Saved 5 charts")
