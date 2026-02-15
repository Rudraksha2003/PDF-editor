"""Remove blank pages from PDF."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/remove-blanks")
async def remove_blank_pages(
    file: UploadFile = File(...),
    threshold: float = Form(0.01, description="Max fraction of non-white pixels to consider blank (0-1)"),
):
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.REMOVE_BLANKS,
            "no_blanks.pdf",
            {"threshold": threshold, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
