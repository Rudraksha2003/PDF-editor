"""Flatten PDF (forms/annotations into static content)."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/flatten")
async def flatten_pdf(
    file: UploadFile = File(...),
    flatten_only_forms: bool = Form(False, description="Only flatten form fields; keep links and other annotations"),
):
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.FLATTEN,
            "flattened.pdf",
            {"input_filenames": [file.filename], "flatten_only_forms": flatten_only_forms},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
