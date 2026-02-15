"""Delete specific pages from a PDF."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.security.validators import validate_page_numbers
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/delete")
async def delete_pages(
    file: UploadFile = File(...),
    pages: str = Form(..., description="Comma-separated page numbers, e.g. 2,4"),
):
    try:
        pages_to_delete = [int(p.strip()) for p in pages.split(",") if p.strip()]
        validate_page_numbers(pages_to_delete, allow_empty=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.DELETE,
            "deleted.pdf",
            {"pages": pages_to_delete, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
