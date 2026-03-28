"""CLI tool to extract structured data from PDFs into Excel."""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from extract import extract_from_text
from pdf_reader import read_pdfs
from schema import load_schema

SAVE_EVERY = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured information from PDFs into Excel."
    )
    parser.add_argument("--pdfs", required=True, help="Path to folder of PDFs.")
    parser.add_argument("--fields", required=True, help="Path to YAML fields file.")
    parser.add_argument("--output", default="results.xlsx", help="Output Excel path.")
    parser.add_argument(
        "--skip-citations",
        action="store_true",
        help="Omit citation fields and NODE chunking.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing .jsonl instead of restarting.",
    )
    return parser.parse_args()


def jsonl_path_for(output: str) -> Path:
    return Path(output).with_suffix(".jsonl")


def archive_old_files(output: str) -> None:
    """Move existing output files to old_files/YYYY-MM-DD_HH-MM-SS/."""
    xlsx = Path(output)
    jsonl = jsonl_path_for(output)

    if not xlsx.exists() and not jsonl.exists():
        return

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    archive = Path("old_files") / ts
    archive.mkdir(parents=True, exist_ok=True)

    for f in (xlsx, jsonl):
        if f.exists():
            shutil.move(str(f), str(archive / f.name))
            print(f"Archived {f} -> {archive / f.name}")


def load_completed(jsonl: Path) -> dict[str, dict]:
    """Load already-processed results from a JSONL file."""
    results: dict[str, dict] = {}
    if not jsonl.exists():
        return results
    for line in jsonl.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            filename = record.pop("_filename")
            results[filename] = record
    return results


def append_jsonl(jsonl: Path, filename: str, data: dict) -> None:
    record = {"_filename": filename, **data}
    with open(jsonl, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_excel(jsonl: Path, output: str) -> None:
    results = load_completed(jsonl)
    if not results:
        return
    df = pd.DataFrame.from_dict(results, orient="index")
    df.index.name = "filename"
    df.to_excel(output)
    print(f"Saved {len(results)} results to {output}")


def main() -> None:
    args = parse_args()

    include_citations = not args.skip_citations
    config = load_schema(args.fields, include_citations=include_citations)
    jsonl = jsonl_path_for(args.output)

    # Resume or restart
    if args.resume:
        completed = load_completed(jsonl)
        print(f"Resuming: {len(completed)} already processed.")
    else:
        archive_old_files(args.output)
        completed = {}

    # Read PDFs
    print(f"Reading PDFs from {args.pdfs}...")
    pdf_texts = read_pdfs(args.pdfs)
    print(f"Found {len(pdf_texts)} PDFs.")

    # Filter out already-completed
    to_process = {k: v for k, v in pdf_texts.items() if k not in completed}
    print(f"Processing {len(to_process)} PDFs ({len(completed)} skipped).")

    # Extract
    count = 0
    for filename, text in tqdm(to_process.items(), desc="Extracting"):
        result = extract_from_text(
            text=text,
            model_class=config.model_class,
            openai_model=config.openai_model,
            system_prompt=config.system_prompt,
            skip_citations=args.skip_citations,
        )
        if result is None:
            print(f"Skipping {filename} due to extraction error.")
            continue

        append_jsonl(jsonl, filename, result)
        count += 1

        if count % SAVE_EVERY == 0:
            save_excel(jsonl, args.output)

    # Final save
    save_excel(jsonl, args.output)
    print("Done.")


if __name__ == "__main__":
    main()
