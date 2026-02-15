"""Convert PDF pages to images (ZIP of JPG/PNG)."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/pdf-to-img")
async def pdf_to_images(
    file: UploadFile = File(...),
    format: str = Form("jpg", description="jpg or png"),
):
    if format not in ("jpg", "png"):
        raise HTTPException(status_code=400, detail="format must be jpg or png")
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.PDF_TO_IMG,
            "images.zip",
            {"format": format, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
