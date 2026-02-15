"""Convert PDF to Office (Word, Excel, PowerPoint). Requires LibreOffice."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/pdf-to-office")
async def pdf_to_office(
    file: UploadFile = File(...),
    format: str = Form("docx", description="docx, xlsx, or pptx"),
):
    if format not in ("docx", "xlsx", "pptx"):
        raise HTTPException(status_code=400, detail="format must be docx, xlsx, or pptx")
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.PDF_TO_OFFICE,
            f"output.{format}",
            {"format": format, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
