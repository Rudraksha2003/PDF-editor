"""Reorder PDF pages (organize PDF)."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.security.validators import validate_page_numbers
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/reorder")
async def reorder_pages(
    file: UploadFile = File(...),
    order: str = Form(..., description="Comma-separated page order, e.g. 3,1,2"),
):
    try:
        page_order = [int(p.strip()) for p in order.split(",") if p.strip()]
        validate_page_numbers(page_order, allow_empty=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.REORDER,
            "reordered.pdf",
            {"order": page_order, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
