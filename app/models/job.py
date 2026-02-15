from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobType(str, Enum):
    # Organize
    MERGE = "merge"
    SPLIT = "split"
    SPLIT_BY_RANGE = "split_by_range"
    DELETE = "delete"
    EXTRACT = "extract"
    REORDER = "reorder"
    # Optimize
    COMPRESS = "compress"
    REPAIR = "repair"
    OCR = "ocr"
    # Convert
    IMG_TO_PDF = "img_to_pdf"
    PDF_TO_IMG = "pdf_to_img"
    PDF_TO_PDFA = "pdf_to_pdfa"
    PDF_TO_TEXT = "pdf_to_text"
    HTML_TO_PDF = "html_to_pdf"
    OFFICE_TO_PDF = "office_to_pdf"
    PDF_TO_OFFICE = "pdf_to_office"
    # Edit
    ROTATE = "rotate"
    CROP = "crop"
    ADD_PAGE_NUMBERS = "add_page_numbers"
    ADD_WATERMARK = "add_watermark"
    ADD_STAMP = "add_stamp"
    FLATTEN = "flatten"
    REMOVE_BLANKS = "remove_blanks"
    EDIT_PDF_EXTRACT = "edit_pdf_extract"
    EDIT_PDF_REPLACE = "edit_pdf_replace"
    EDIT_PDF_PREPARE = "edit_pdf_prepare"
    # Security
    PROTECT = "protect"
    UNLOCK = "unlock"
    REDACT = "redact"
    SIGN_PDF = "sign_pdf"
    SANITIZE = "sanitize"
    COMPARE_PDF = "compare_pdf"
    # Extract / analysis (file output)
    EXTRACT_IMAGES = "extract_images"

class Job(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus
    input_paths: List[str]
    output_path: str
    created_at: datetime
    params: Optional[Dict] = None
    error: Optional[str] = None
    output_filename: Optional[str] = None  # e.g. "result.zip" for split