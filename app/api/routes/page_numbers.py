"""Add page numbers to PDF (e.g. 'Page 1 of N')."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/page-numbers")
async def add_page_numbers(
    file: UploadFile = File(...),
    template: str = Form("Page {n} of {total}", description="Use {n} for page number, {total} for total"),
    position: str = Form("bottom_center", description="bottom_center, bottom_right, top_center, etc."),
):
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.ADD_PAGE_NUMBERS,
            "numbered.pdf",
            {"template": template, "position": position, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
