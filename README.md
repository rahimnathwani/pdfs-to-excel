# pdfs-to-excel

Extract structured information from a folder of PDFs into an Excel spreadsheet using LLMs. Define what to extract in a YAML file.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Tesseract](https://github.com/tesseract-ocr/tesseract) installed and on PATH (for OCR fallback)
- OpenAI API key in a `.env` file or set as `OPENAI_API_KEY` environment variable

## Installation

```bash
uv sync
```

## Usage

```bash
uv run python main.py --pdfs ./contracts --fields fields.yaml --output results.xlsx
```

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--pdfs` | Yes | — | Path to folder of PDFs |
| `--fields` | Yes | — | Path to YAML fields file |
| `--output` | No | `results.xlsx` | Output Excel path |
| `--skip-citations` | No | — | Omit citation fields and NODE chunking |
| `--resume` | No | — | Resume from existing `.jsonl` instead of restarting |

### Resume / Restart

**Default (no `--resume`):** If previous output files exist, they are moved to `old_files/<timestamp>/` before starting fresh.

**With `--resume`:** Loads the existing `.jsonl` file, skips already-processed PDFs, and appends new results.

Results are saved incrementally to a `.jsonl` file after each PDF, and converted to Excel every 10 PDFs.

## YAML Fields Format

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

### Supported field types

- `string` — text
- `integer` — whole number
- `float` — decimal number
- `boolean` — true/false

Add `choices` to constrain values to a fixed set.

### Citations

By default, the tool adds `_citation` fields that reference the source text for each extracted value. Use `--skip-citations` to disable this.
