"""Measure response lengths and statement-specific key-term coverage."""

import csv
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "responses.csv"
OUTPUT_PATH = BASE_DIR / "results.csv"

# Each statement has its own checklist; a term is found when any listed spelling
# occurs as a lowercase substring of the response.
KEY_TERMS = {
    1: [
        ("Mask Fit (function/video)", ["mask fit function", "run mask fit", "mask fit video", "mask fit feature"]),
        ("myAir app", ["myair"]),
        ("mask user guide", ["user guide", "user instructions"]),
    ],
    2: [
        ("humidity level", ["humidity level", "humidity setting"]),
        ("increase", ["increas", "turn up", "raise"]),
    ],
    3: [
        ("humidity level", ["humidity level", "humidity setting", "humidifier setting", "humidifier level"]),
        ("decrease", ["decreas", "lower", "turn down", "reduc"]),
        ("tube temperature", ["tube temperature", "tube temp"]),
    ],
    4: [
        ("mouth", ["mouth"]),
        ("chin strap", ["chin strap"]),
        ("full face mask", ["full face mask"]),
    ],
    5: [
        ("power / AC adaptor", ["ac adaptor", "power supply", "power cord", "power source", "plugged"]),
        ("plug fully inserted", ["fully inserted", "plugged in", "plug is"]),
    ],
    6: [
        ("humidifier tub", ["humidifier tub"]),
        ("side cover", ["side cover"]),
        ("assembled", ["assembl"]),
        ("damaged / cracked", ["damage", "crack"]),
        ("click in place", ["click"]),
        ("replacement", ["replac"]),
    ],
    7: [
        ("wireless coverage", ["coverage", "wireless signal", "cellular signal"]),
        ("bedside table", ["bedside"]),
        ("drawer / floor", ["drawer", "floor"]),
        ("signal icon / bars", ["icon", "bars"]),
        ("Airplane Mode", ["airplane mode"]),
        ("care provider", ["care provider"]),
    ],
    8: [
        ("deep breath", ["deep breath", "deep enough"]),
        ("Start therapy/Standby button", ["start therapy/standby", "standby button", "start button"]),
        ("headgear", ["headgear"]),
        ("air tubing / both ends", ["both ends", "air tubing", "tubing"]),
        ("leak", ["leak"]),
    ],
    9: [
        ("incompatible mask", ["incompatible", "compatible"]),
        ("ResMed-recommended equipment", ["recommended by resmed", "resmed-recommended", "resmed recommended"]),
        ("ResMed.com / contact ResMed", ["resmed.com", "contact resmed"]),
        ("nasal pillows / 7 cm H2O", ["nasal pillows", "7 cm"]),
        ("conduit mask", ["conduit"]),
    ],
}


def score_response(statement: int, response_text: str) -> dict[str, object]:
    """Return checklist matches for one response using case-insensitive substring matching."""
    text = response_text.lower()
    found = [
        term
        for term, spellings in KEY_TERMS[statement]
        if any(spelling in text for spelling in spellings)
    ]
    all_terms = [term for term, _ in KEY_TERMS[statement]]
    missing = [term for term in all_terms if term not in found]
    return {
        "key_terms_found": len(found),
        "key_terms_total": len(all_terms),
        "key_term_match": len(found) / len(all_terms),
        "terms_found": "; ".join(found),
        "terms_missing": "; ".join(missing),
    }


def main() -> None:
    """Create the compact results table and print the requested summaries."""
    if not INPUT_PATH.is_file():
        raise FileNotFoundError(f"Could not find extracted data: {INPUT_PATH}")

    responses = pd.read_csv(INPUT_PATH, keep_default_na=False)
    responses["statement"] = responses["statement"].astype(int)
    responses["run"] = responses["run"].astype(int)

    # Derive length and checklist measurements from the two extracted text fields.
    responses["words"] = responses["response_text"].map(lambda text: len(text.split()))
    responses["characters"] = responses["response_text"].map(len)
    responses["words_no_boilerplate"] = responses[
        "response_text_no_boilerplate"
    ].map(lambda text: len(text.split()))
    scores = responses.apply(
        lambda row: score_response(row["statement"], row["response_text"]),
        axis=1,
        result_type="expand",
    )
    responses = pd.concat([responses, scores], axis=1)

    # The result file omits only the two long text columns to stay easy to inspect.
    results = responses.drop(
        columns=["response_text", "response_text_no_boilerplate"]
    )
    results.to_csv(OUTPUT_PATH, index=False, quoting=csv.QUOTE_MINIMAL)

    averages = responses.groupby("wording")[
        ["words", "words_no_boilerplate", "characters", "key_term_match"]
    ].mean()
    print("\nAverage response metrics by wording:")
    print(averages.round(3).to_string())

    for metric, title in [
        ("key_term_match", "Key-term match by statement and wording"),
        ("words_no_boilerplate", "Words without boilerplate by statement and wording"),
    ]:
        pivot = responses.pivot_table(
            index="statement", columns="wording", values=metric, aggfunc="mean"
        )
        print(f"\n{title}:")
        print(pivot.round(3).to_string())

    source_counts = responses.assign(
        source_cited=responses["source_cited"].replace("", "None")
    ).groupby(["wording", "source_cited"]).size().unstack(fill_value=0)
    print("\nSource citations by wording:")
    print(source_counts.to_string())

    boilerplate_counts = responses.assign(
        boilerplate_count=(responses["has_boilerplate"] == "Y").astype(int)
    ).pivot_table(
        index="statement",
        columns="wording",
        values="boilerplate_count",
        aggfunc="sum",
        fill_value=0,
    )
    print("\nResponses with boilerplate by statement and wording:")
    print(boilerplate_counts.to_string())
    print(f"\nSaved {len(results)} analyzed responses to {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
