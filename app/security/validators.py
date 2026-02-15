import re

from pypdf import PdfReader

ALLOWED_PDF_CONTENT_TYPES = (
    "application/pdf",
    "application/octet-stream",
    "application/x-pdf",
)
ALLOWED_PDF_EXTENSIONS = (".pdf",)
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
MAX_PAGES = 200  # safe default
MAX_PAGE_NUMBER = 50_000  # upper bound for a single page number (avoid abuse)

# UUID v4 regex for validating job_id (path parameter)
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[4][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _check_file_type(upload_file, allowed_content_types, allowed_extensions, expected_label: str):
    """Raise ValueError if content_type or filename extension is not allowed."""
    ct = (upload_file.content_type or "").strip().lower()
    fn = (upload_file.filename or "").lower()
    has_valid_ext = fn and any(fn.endswith(ext) for ext in allowed_extensions)
    has_valid_ct = ct and ct in allowed_content_types
    # Accept if either content-type or extension indicates the right type (e.g. Swagger may send wrong ct)
    if has_valid_ct or has_valid_ext:
        return
    if ct and not has_valid_ext:
        raise ValueError(f"Invalid file type. Expected {expected_label}.")
    if fn:
        raise ValueError(f"Invalid file. Expected {expected_label} (e.g. {', '.join(allowed_extensions)}).")
    raise ValueError("Invalid file: missing filename and content type.")


def validate_upload(file):
    """Validate that the upload is a PDF (content-type and extension)."""
    _check_file_type(
        file,
        ALLOWED_PDF_CONTENT_TYPES,
        ALLOWED_PDF_EXTENSIONS,
        "PDF",
    )


def validate_upload_pdf(file):
    """Alias for validate_upload. Use validate_upload for new code."""
    validate_upload(file)


def validate_file_size(size: int, max_size: int = MAX_FILE_SIZE) -> None:
    """Raise ValueError if size exceeds max_size (default MAX_FILE_SIZE)."""
    if size <= 0:
        raise ValueError("File is empty.")
    if size > max_size:
        mb = max_size // (1024 * 1024)
        raise ValueError(f"File too large. Maximum size is {mb} MB.")


def validate_job_id(job_id: str) -> None:
    """Raise ValueError if job_id is not a valid UUID v4 format."""
    if not job_id or not UUID_PATTERN.match(job_id.strip()):
        raise ValueError("Invalid job ID format.")


def validate_upload_image(file):
    """Validate that the upload is an image (JPEG, PNG, WebP, GIF)."""
    _check_file_type(
        file,
        ALLOWED_IMAGE_CONTENT_TYPES,
        ALLOWED_IMAGE_EXTENSIONS,
        "image (JPEG, PNG, WebP, GIF)",
    )

def validate_pdf_limits(file_path: str):
    reader = PdfReader(file_path)
    if len(reader.pages) > MAX_PAGES:
        raise ValueError("PDF exceeds maximum page limit")


def validate_page_numbers(
    page_list: list[int],
    *,
    min_val: int = 1,
    max_val: int = MAX_PAGE_NUMBER,
    allow_empty: bool = False,
) -> None:
    """Raise ValueError if any page number is out of bounds or invalid."""
    if not allow_empty and not page_list:
        raise ValueError("At least one page required")
    bad = [p for p in page_list if not (min_val <= p <= max_val)]
    if bad:
        raise ValueError(
            f"Page number(s) {bad} are out of range. Valid range: {min_val}–{max_val}."
        )
