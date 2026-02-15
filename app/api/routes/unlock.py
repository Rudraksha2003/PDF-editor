"""Unlock PDF (remove password protection)."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/unlock")
async def unlock_pdf(
    file: UploadFile = File(...),
    password: str = Form(..., description="Current PDF password"),
):
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.UNLOCK,
            "unlocked.pdf",
            {"password": password, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
