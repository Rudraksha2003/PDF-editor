"""Crop PDF pages (margin in points: left, bottom, right, top)."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/crop")
async def crop_pdf(
    file: UploadFile = File(...),
    left: float = Form(0, description="Left margin (points)"),
    bottom: float = Form(0, description="Bottom margin (points)"),
    right: float = Form(0, description="Right margin (points)"),
    top: float = Form(0, description="Top margin (points)"),
):
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.CROP,
            "cropped.pdf",
            {"left": left, "bottom": bottom, "right": right, "top": top, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
