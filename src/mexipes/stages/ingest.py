import hashlib
import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

import fitz  # PyMuPDF

from mexipes.storage import RecipeStore

logger = logging.getLogger(__name__)


def compute_md5(filepath: Path) -> str:
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_valid_pdf(filepath: Path) -> bool:
    """Validate that the file is a readable PDF using PyMuPDF."""
    try:
        with fitz.open(filepath) as doc:
            return doc.page_count > 0
    except Exception as e:
        logger.error(f"Invalid PDF {filepath}: {e}")
        return False


def ingest_pdfs(store: RecipeStore, staging_dir: Path) -> None:
    """Scans staging_dir for PDFs, dedups by MD5, validates, and registers them in the store."""
    staging_path = Path(staging_dir)
    if not staging_path.exists():
        print(f"Staging directory does not exist: {staging_path}")
        return

    rejected_dir = store.data_dir / "rejected"
    rejected_dir.mkdir(exist_ok=True)

    # 1. Gather all existing publication hashes
    existing_hashes = {}
    publications_dir = store.data_dir / "publications"
    if publications_dir.exists():
        for pub_path in publications_dir.iterdir():
            if pub_path.is_dir() and pub_path.name.isdigit():
                info_file = pub_path / "publication_info.json"
                if info_file.exists():
                    try:
                        info = json.loads(info_file.read_text(encoding="utf-8"))
                        if "md5" in info:
                            existing_hashes[info["md5"]] = pub_path
                    except Exception:
                        pass

    # 2. Scan staging for PDFs
    pdf_files = sorted([f for f in staging_path.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])

    if not pdf_files:
        print("No PDF files found in staging.")
        return

    print(f"Found {len(pdf_files)} PDF files in staging. Processing...")

    moved_count = 0
    skipped_count = 0
    invalid_count = 0

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")

        # A. Validate PDF
        if not is_valid_pdf(pdf_file):
            print("  -> ERROR: Corrupted or unreadable PDF. Moving to rejected/")
            shutil.move(pdf_file, rejected_dir / pdf_file.name)
            invalid_count += 1
            continue

        # B. Check MD5 hash
        md5_hash = compute_md5(pdf_file)
        if md5_hash in existing_hashes:
            match_path = existing_hashes[md5_hash]
            print(f"  -> Duplicate found (matches publication ID {match_path.name}). Moving to rejected/")
            shutil.move(pdf_file, rejected_dir / f"dup_{match_path.name}_{pdf_file.name}")
            skipped_count += 1
            continue

        # C. Register new publication
        next_publication_id = store.get_next_publication_id()
        publication_dir = store.get_publication_dir(next_publication_id)

        # Copy/move PDF to destination as source.pdf
        dest_pdf = publication_dir / "source.pdf"
        shutil.move(pdf_file, dest_pdf)

        # Write publication_info.json
        pub_info = {
            "publication_id": next_publication_id,
            "original_filename": pdf_file.name,
            "md5": md5_hash,
            "ingested_at": datetime.now(UTC).isoformat(),
            "status": "registered",
        }
        (publication_dir / "publication_info.json").write_text(json.dumps(pub_info, indent=4), encoding="utf-8")

        print(f"  -> Successfully registered Publication ID {next_publication_id}")
        existing_hashes[md5_hash] = publication_dir
        moved_count += 1

    print(
        f"\nIngestion summary:\n"
        f"  - Ingested & registered: {moved_count}\n"
        f"  - Skipped duplicates: {skipped_count}\n"
        f"  - Invalid/corrupt rejected: {invalid_count}"
    )
