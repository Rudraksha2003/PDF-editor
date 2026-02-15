from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/split")
async def split_pdf(file: UploadFile = File(...)):
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.SPLIT,
            "split_page_1.pdf",
            {"input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
