"""Add text or PDF watermark to every page."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/watermark")
async def add_watermark(
    file: UploadFile = File(...),
    text: str = Form(..., description="Watermark text"),
    opacity: float = Form(0.5, ge=0.1, le=1.0),
):
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.ADD_WATERMARK,
            "watermarked.pdf",
            {"text": text, "opacity": opacity, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
