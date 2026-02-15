"""Sanitize PDF - remove scripts, embedded files, metadata, links, fonts per user options."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


def _form_bool(value: str) -> bool:
    return (value or "").strip().lower() in ("true", "1", "yes", "on")


@router.post("/sanitize")
async def sanitize_pdf(
    file: UploadFile = File(...),
    remove_javascript: str = Form("true", description="Remove JavaScript actions and scripts"),
    remove_embedded_files: str = Form("true", description="Remove embedded files"),
    remove_xmp_metadata: str = Form("false", description="Remove XMP metadata"),
    remove_document_metadata: str = Form("false", description="Remove document info (title, author, etc.)"),
    remove_links: str = Form("false", description="Remove external links and launch actions"),
    remove_fonts: str = Form("false", description="Remove embedded fonts"),
):
    opts = {
        "remove_javascript": _form_bool(remove_javascript),
        "remove_embedded_files": _form_bool(remove_embedded_files),
        "remove_xmp_metadata": _form_bool(remove_xmp_metadata),
        "remove_document_metadata": _form_bool(remove_document_metadata),
        "remove_links": _form_bool(remove_links),
        "remove_fonts": _form_bool(remove_fonts),
    }
    if not any(opts.values()):
        raise HTTPException(
            status_code=400,
            detail="Select at least one sanitisation option.",
        )
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.SANITIZE,
            "sanitized.pdf",
            {"input_filenames": [file.filename], **opts},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
