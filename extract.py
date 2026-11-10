"""Extract Dawn's 54 troubleshooting responses from the source PDF."""

import csv
import re
import string
from pathlib import Path
from typing import Optional

import pdfplumber


BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "AI-CPAP Troubleshooting Statements.pdf"
CSV_PATH = BASE_DIR / "responses.csv"

SECTION_MARKER = "Dawn GenAI responses on resmed.com website"
HEADER_RE = re.compile(
    r"^\s*(?:(Resmed Airsense 11)\s+)?Response\s+([1-3]):\s*$",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^\s*([1-9])\.\s+(.+?)\s*$")
LINK_RE = re.compile(r"Learn More:\s*([^\s]+?\.pdf)\b", re.IGNORECASE)

BOILERPLATE = (
    "For a holistic view of your sleep health and to identify risk factors, "
    "consider taking our sleep assessment and Our fun AI SelfieScreener tool "
    "can provide insights into your sleep health in just minutes. Always "
    "consult with a licensed healthcare professional for medical advice, "
    "diagnosis and treatment options."
)
BOILERPLATE_FRAGMENT = "Sleep-assessment append"

OUTPUT_COLUMNS = [
    "statement",
    "problem",
    "wording",
    "run",
    "source_cited",
    "has_boilerplate",
    "response_text",
    "response_text_no_boilerplate",
]


def _normalize_prompt_text(text: str) -> str:
    """Lowercase text and discard punctuation so echoed prompt fragments compare cleanly."""
    normalized = " ".join(
        "".join(character for character in text.lower() if character not in string.punctuation)
        .split()
    )
    # One copied device prompt includes an extra article before the model name.
    return re.sub(r"\bi have a resmed\b", "i have resmed", normalized)


def _clean_body(
    lines: list[str], prompt: str
) -> tuple[str, Optional[str], str, str]:
    """Join body lines, remove leading prompt echoes, and extract a cited PDF filename."""
    bullets: list[str] = []
    current_bullet = ""

    # Treat a dash as a bullet boundary and other lines as wrapped continuation text.
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-"):
            if current_bullet:
                bullets.append(current_bullet)
            current_bullet = stripped[1:].strip()
        elif current_bullet:
            current_bullet = f"{current_bullet} {stripped}"
        else:
            bullets.append(stripped)
    if current_bullet:
        bullets.append(current_bullet)

    # Remove only leading bullets that repeat text from the prompt.
    prompt_normalized = _normalize_prompt_text(prompt)
    while bullets:
        first_normalized = _normalize_prompt_text(bullets[0])
        if first_normalized and first_normalized in prompt_normalized:
            bullets.pop(0)
        else:
            break

    response_text = " ".join(bullets)

    # A citation can be attached directly to the response's final word.
    link_match = LINK_RE.search(response_text)
    source_cited = link_match.group(1).rstrip(".,;:") if link_match else None
    if link_match:
        response_text = (
            response_text[: link_match.start()] + response_text[link_match.end() :]
        ).strip()

    # Keep the source text intact except for the requested boilerplate removal.
    response_text = re.sub(r"\s+", " ", response_text).strip()
    no_boilerplate = re.sub(
        re.escape(BOILERPLATE), "", response_text, flags=re.IGNORECASE
    )
    no_boilerplate = re.sub(
        re.escape(BOILERPLATE_FRAGMENT), "", no_boilerplate, flags=re.IGNORECASE
    )
    no_boilerplate = re.sub(r"\s+", " ", no_boilerplate).strip()
    has_boilerplate = (
        "Y"
        if re.search(re.escape(BOILERPLATE), response_text, re.IGNORECASE)
        or re.search(re.escape(BOILERPLATE_FRAGMENT), response_text, re.IGNORECASE)
        else "N"
    )
    return response_text, source_cited, no_boilerplate, has_boilerplate


def extract_responses() -> list[dict[str, object]]:
    """Read the PDF and parse only the response section into response records."""
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f"Could not find input PDF: {PDF_PATH}")

    with pdfplumber.open(PDF_PATH) as pdf:
        document_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Ignore the manual answer key by starting only after the explicit Part B marker.
    marker_position = document_text.casefold().find(SECTION_MARKER.casefold())
    if marker_position < 0:
        raise ValueError(f"Could not find section marker: {SECTION_MARKER}")
    response_section = document_text[marker_position + len(SECTION_MARKER) :]

    records: list[dict[str, object]] = []
    current_statement: int | None = None
    current_problem = ""
    current_response: dict[str, object] | None = None
    response_lines: list[str] = []

    def save_current_response() -> None:
        nonlocal current_response, response_lines
        if current_response is None:
            return
        wording = str(current_response["wording"])
        prompt = current_problem
        if wording == "Device named":
            prompt = f"{prompt} I have Resmed Airsense 11 CPAP machine."
        text, source, text_without_boilerplate, has_boilerplate = _clean_body(
            response_lines, prompt
        )
        current_response.update(
            {
                "source_cited": source or "",
                "has_boilerplate": has_boilerplate,
                "response_text": text,
                "response_text_no_boilerplate": text_without_boilerplate,
            }
        )
        records.append(current_response)
        current_response = None
        response_lines = []

    for raw_line in response_section.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = HEADER_RE.fullmatch(line)
        if header_match:
            save_current_response()
            is_device_named = header_match.group(1) is not None
            current_response = {
                "statement": current_statement,
                "problem": current_problem,
                "wording": "Device named" if is_device_named else "Plain",
                "run": int(header_match.group(2)),
            }
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            statement_number = int(heading_match.group(1))
            # A numbered heading marks a new problem only when no response is open.
            if current_response is not None or current_statement is None or (
                statement_number == current_statement + 1
            ):
                save_current_response()
                current_statement = statement_number
                current_problem = heading_match.group(2).strip()
                continue

        if current_response is not None:
            response_lines.append(line)
        elif current_statement is not None:
            # Statement headings may wrap before the first response header.
            current_problem = f"{current_problem} {line}".strip()

    save_current_response()

    if len(records) != 54:
        raise ValueError(f"Expected exactly 54 responses, found {len(records)}")
    if {record["statement"] for record in records} != set(range(1, 10)):
        raise ValueError("The extracted responses do not cover statements 1 through 9")

    return records


def main() -> None:
    """Write the extracted records to a clean CSV file."""
    records = extract_responses()
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    print(f"Extracted {len(records)} responses to {CSV_PATH.name}")


if __name__ == "__main__":
    main()
