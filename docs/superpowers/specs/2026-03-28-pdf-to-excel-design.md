# PDF-to-Excel Extraction Tool — Design Spec

## Overview

A generic Python CLI tool that extracts structured information from a folder of PDFs into an Excel spreadsheet. The user defines what to extract in a YAML file. The tool handles PDF text extraction (with OCR fallback), sends text to OpenAI for structured extraction using Pydantic models, and outputs an Excel file.

## Architecture

Flat module structure — five files at the project root:

| File | Responsibility |
|---|---|
| `main.py` | CLI (argparse), orchestration, resume/restart logic, periodic Excel saves |
| `pdf_reader.py` | PDF to text (pymupdf + pytesseract OCR fallback, Arabic + English) |
| `schema.py` | YAML parsing, validation, dynamic Pydantic model generation |
| `extract.py` | NODE chunking, OpenAI structured extraction, citation resolution |
| `fields.yaml` | Example extraction fields file |
| `README.md` | Usage instructions with `uv run` |

## YAML Fields Format

The user defines extraction fields in a YAML file:

```yaml
model: gpt-5-mini
system_prompt: "You are a lawyer. Answer based only on the provided document."

fields:
  - name: client_name
    type: string
    description: "The full name of the buyer"

  - name: sale_date
    type: string
    description: "Date of sale in YYYY-MM-DD format"

  - name: property_type
    type: string
    description: "Type of property"
    choices: ["Villa", "House", "Apartment"]

  - name: built_up_area
    type: integer
    description: "Size in square meters. Return 0 if unknown."
```

Supported field types: `string`, `integer`, `float`, `boolean`. Optional `choices` for enum constraints.

The `model` and `system_prompt` fields live in this file since they are closely tied to the extraction task.

## PDF Reader (`pdf_reader.py`)

- Takes a folder path, finds all `.pdf` files.
- For each PDF, tries `pymupdf` text extraction first.
- If extracted text is empty or too short (< 50 chars), falls back to pytesseract OCR with `ara+eng` language setting.
- Returns a dict of `{filename: text_content}`.
- Skips non-PDF files silently.

## Schema Builder (`schema.py`)

- Reads the YAML file, validates it (checks required keys, valid types).
- Builds a Pydantic model dynamically with `pydantic.create_model()`.
- Maps YAML types: `string` -> `str`, `integer` -> `int`, `float` -> `float`, `boolean` -> `bool`.
- For fields with `choices`, uses `Literal["a", "b", "c"]` as the type.
- If citations are enabled, adds `{name}_citation: str | None` for each field.
- Returns the Pydantic model, the model name (for OpenAI), and the system prompt.

## LLM Extraction (`extract.py`)

- Uses OpenAI's `client.responses.parse()` with the dynamically-built Pydantic model as `text_format`.
- If citations are enabled:
  - Text is chunked (500 chars) with `[NODE N]` markers prepended to each chunk.
  - After extraction, citation node references are resolved back to the actual text chunk.
- If `--skip-citations` is set, no NODE markers or citation fields are added.
- On error for a single file, logs the error and continues to the next file.

## CLI (`main.py`)

```
python main.py --pdfs ./contracts --fields fields.yaml --output results.xlsx
```

### Arguments

- `--pdfs` (required): path to folder of PDFs.
- `--fields` (required): path to YAML fields file.
- `--output` (default: `results.xlsx`): output Excel path.
- `--skip-citations`: omit citation fields and NODE chunking.
- `--resume`: resume from existing `.jsonl` instead of restarting.

### Restart/Resume Behavior

**Default (no `--resume`):** If `results.jsonl` or `results.xlsx` already exist at the output path, move them to `old_files/YYYY-MM-DD_HH-MM-SS/` before starting fresh.

**With `--resume`:** Load existing `results.jsonl`, skip already-processed filenames, append new results.

### Incremental Saves

- Results are appended to a `.jsonl` file (one JSON line per completed PDF) as each file is processed.
- Every 10 completed PDFs (and once at the end), the `.jsonl` is converted to the output `.xlsx`.
- JSONL is used because it is human-readable, append-friendly, and cross-platform.

## Cross-platform

- Uses `pathlib.Path` throughout instead of `os.path.join`.
- pytesseract on Windows requires Tesseract installed and on PATH — the tool checks for it on startup and gives a clear error if missing.
- No shell-specific or Unix-specific logic.

## Dependencies

- `openai` — LLM API calls with Pydantic structured output
- `pydantic` — dynamic model generation
- `pymupdf` — PDF text extraction
- `pytesseract` — OCR fallback for image-based PDFs
- `Pillow` — required by pytesseract for image handling
- `pyyaml` — YAML parsing
- `openpyxl` — Excel writing
- `pandas` — DataFrame to Excel conversion
- `tqdm` — progress bar

## README

The README will document:
- What the tool does (one-liner)
- Prerequisites (Python 3.12+, Tesseract for OCR, OpenAI API key)
- Installation with `uv`
- Usage examples with `uv run`
- YAML fields format reference
- Resume and citation options
