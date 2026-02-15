"""Redact PDF - black out text matching search strings."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/redact")
async def redact_pdf(
    file: UploadFile = File(...),
    search: str = Form(..., description="Comma-separated phrases to redact (case-sensitive)"),
):
    phrases = [p.strip() for p in search.split(",") if p.strip()]
    if not phrases:
        raise HTTPException(status_code=400, detail="At least one search phrase required")
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.REDACT,
            "redacted.pdf",
            {"phrases": phrases, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
