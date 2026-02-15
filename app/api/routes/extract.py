"""Extract specific pages from a PDF into a new PDF."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.security.validators import validate_page_numbers
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/extract")
async def extract_pages(
    file: UploadFile = File(...),
    pages: str = Form(..., description="Comma-separated page numbers, e.g. 1,3,5-7"),
):
    try:
        page_list = []
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                page_list.extend(range(int(a.strip()), int(b.strip()) + 1))
            else:
                page_list.append(int(part))
        validate_page_numbers(page_list, allow_empty=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.EXTRACT,
            "extracted.pdf",
            {"pages": page_list, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
