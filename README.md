# CPAP Troubleshooting Response Analysis

## About

Part of a human factors portfolio case study evaluating whether Resmed’s AI assistant, Dawn, gives the same troubleshooting guidance as the Resmed AirSense 11 user manual.

Nine troubleshooting problem statements from the manual (p.18) were each entered into Dawn under two conditions:

Plain: the problem statement word for word from the manual (3 runs)
Device named: the same statement followed by “I have Resmed Airsense 11 CPAP machine.” (3 runs)

That’s 9 statements × 2 conditions × 3 runs = 54 responses, each scored against the manual’s causes and solutions.

Author: Alyssa Mendes, MS Human Factors student, Embry-Riddle Aeronautical University

My role: I designed the study, collected all 54 responses, built the answer key from the AirSense 11 manual, and made the final scoring decisions. An AI assistant (Claude) applied the yes/no scoring rules for a first-pass draft. I reviewed the borderline cases and revised four of the rules (for example, counting “use a heated tube” as addressing tube temperature) before finalizing the scores. The analysis scripts were developed with AI coding assistants (Claude, GitHub Copilot) and checked against hand-calculated expected results.

This is an independent personal project. It was not conducted through, sponsored by, or reviewed by Embry-Riddle, and is not affiliated with or endorsed by Resmed. Responses were collected in November 2026; Dawn’s answers may have changed since.

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
- `charts.py` reads `results.csv` and creates `average_words_by_statement.png`,
  `key_term_match_by_statement.png`, `document_links_by_wording.png`,
  `document_links_stacked.png`, and `boilerplate_by_statement.png`.
- `scores.py` joins `hand_scores.csv` with `results.csv`, recalculates manual
  coverage, prints hand-score summaries, and creates
  `coverage_by_statement.png`, `issues_by_statement.png`,
  `issue_types_by_wording.png`, `coverage_dumbbell.png`, and `runs_grid.png`.
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
`issues_by_statement.png`, `issue_types_by_wording.png`,
`coverage_dumbbell.png`, and `runs_grid.png`.

The extraction and analysis scripts create `responses.csv` and `results.csv`;
these CSVs are ignored because they contain response text or derived response
data. The charts are summary-level aggregate outputs and are included:
`average_words_by_statement.png`, `key_term_match_by_statement.png`,
`document_links_by_wording.png`, `boilerplate_by_statement.png`, and
`document_links_stacked.png`, plus the five charts produced by `scores.py`.
