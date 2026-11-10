# CPAP Troubleshooting Response Analysis

This project extracts 54 troubleshooting responses from a PDF, measures each
response's length and key-term coverage, and produces summary tables and charts.
A separate scoring script combines the analysis with human-entered hand scores
to calculate manual coverage and issue counts.

The source PDF and generated response-data CSVs are excluded from the repository
because they contain source material or response text. The hand-score file and
summary chart images are included. Keep the source PDF in this folder locally
before running extraction.

## Files

- `extract.py` reads the PDF and writes the 54 parsed responses to
  `responses.csv`.
- `analyze.py` measures response lengths and statement-specific key-term
  matches, prints summary tables, and writes `results.csv`.
- `charts.py` reads `results.csv` and creates four comparison charts.
- `scores.py` joins `hand_scores.csv` with `results.csv`, recalculates manual
  coverage, prints hand-score summaries, and creates three additional charts.
- `hand_scores.csv` contains the human ratings used by `scores.py`.
- `requirements.txt` lists the Python packages used by the scripts.
- `.gitignore` excludes the PDF, response-data CSVs, spreadsheet files, and
  virtual environment while allowing the hand scores and chart PNGs.

## Setup

Use Python 3.9 or later. From this folder, create and activate a virtual
environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Place the source PDF, named `AI-CPAP Troubleshooting Statements.pdf`, in this
folder. The included `hand_scores.csv` is used by the scoring step.

## Run the scripts

Run the response extraction, analysis, and charting scripts in order:

```bash
python extract.py
python analyze.py
python charts.py
```

To merge the human scores after `results.csv` has been created, run:

```bash
python scores.py
```

`scores.py` reads `hand_scores.csv` only from this folder. It writes
`final_results.csv` and the charts `coverage_by_statement.png`,
`issues_by_statement.png`, and `issue_types_by_wording.png`.

The extraction and analysis scripts create `responses.csv` and `results.csv`;
these CSVs are ignored because they contain response text or derived response
data. The charts are summary-level aggregate outputs and are included.

## Validation and AI assistance

The analysis was developed with AI coding assistants and checked against the
expected results in the project instructions, including response counts,
summary metrics, hand-score totals, and representative extracted text. The
hand-score pipeline's reported totals and statement-level summaries matched
those expected results during validation.
