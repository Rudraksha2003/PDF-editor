"""Generate download filenames from job type and original input filenames."""
import os
import re
from app.models.job import JobType


def _safe_basename(name: str, max_len: int = 80) -> str:
    """Get a safe filename base from an original name (no extension, no bad chars)."""
    if not name or not name.strip():
        return "document"
    base = os.path.splitext(name.strip())[0]
    base = re.sub(r'[^\w\s\-_.]', "_", base)
    base = re.sub(r'[\s]+', "_", base).strip("._")
    return base[:max_len] if base else "document"


# Suffix to append before extension for each job type (empty = keep base only, e.g. for pdf_to_office)
JOB_SUFFIX = {
    JobType.MERGE: "_merge",
    JobType.SPLIT: "_split",
    JobType.SPLIT_BY_RANGE: "_split_ranges",
    JobType.DELETE: "_delete",
    JobType.EXTRACT: "_extract",
    JobType.REORDER: "_reorder",
    JobType.COMPRESS: "_compress",
    JobType.REPAIR: "_repaired",
    JobType.OCR: "_ocr",
    JobType.IMG_TO_PDF: "_images",
    JobType.PDF_TO_IMG: "_images",
    JobType.PDF_TO_PDFA: "_pdfa",
    JobType.PDF_TO_TEXT: "_text",
    JobType.HTML_TO_PDF: "_pdf",
    JobType.OFFICE_TO_PDF: "_pdf",
    JobType.ROTATE: "_rotate",
    JobType.CROP: "_crop",
    JobType.ADD_PAGE_NUMBERS: "_numbered",
    JobType.ADD_WATERMARK: "_watermark",
    JobType.ADD_STAMP: "_stamp",
    JobType.FLATTEN: "_flatten",
    JobType.REMOVE_BLANKS: "_no_blanks",
    JobType.PROTECT: "_protected",
    JobType.UNLOCK: "_unlocked",
    JobType.REDACT: "_redacted",
    JobType.SIGN_PDF: "_signed",
    JobType.SANITIZE: "_sanitized",
    JobType.COMPARE_PDF: "_compare",
    JobType.EXTRACT_IMAGES: "_images",
}

# Job types that output ZIP (use .zip extension when not set by output_path)
ZIP_OUTPUT_TYPES = {
    JobType.SPLIT,
    JobType.SPLIT_BY_RANGE,
    JobType.PDF_TO_IMG,
    JobType.EXTRACT_IMAGES,
    JobType.COMPARE_PDF,
}


def make_output_filename(
    job_type: JobType,
    input_filenames: list[str] | None,
    output_path: str,
) -> str:
    """
    Build a download filename from job type and original input names.
    Uses the first input filename as base, appends a suffix, and uses extension from output_path.
    """
    names = input_filenames or []
    base = _safe_basename(names[0]) if names else "document"
    suffix = JOB_SUFFIX.get(job_type, "")
    ext = os.path.splitext(output_path)[1].lower()
    if not ext and job_type in ZIP_OUTPUT_TYPES:
        ext = ".zip"
    if not ext:
        ext = ".pdf"
    name = f"{base}{suffix}{ext}"
    return name
