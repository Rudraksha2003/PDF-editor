"""Compress PDF to reduce file size."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/compress")
async def compress_pdf(
    file: UploadFile = File(...),
    method: str = Form("quality", description="Compression method: quality or file_size"),
    compression_level: int = Form(5, ge=1, le=9, description="Compression level 1-9 (quality mode)"),
    desired_size: float = Form(0, ge=0, description="Target size (file_size mode)"),
    desired_size_unit: str = Form("MB", description="Unit: KB or MB"),
    grayscale: bool = Form(False, description="Apply grayscale for compression"),
):
    if method not in ("quality", "file_size"):
        method = "quality"
    if desired_size_unit not in ("KB", "MB"):
        desired_size_unit = "MB"
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.COMPRESS,
            "compressed.pdf",
            {
                "input_filenames": [file.filename],
                "method": method,
                "compression_level": compression_level,
                "desired_size": desired_size,
                "desired_size_unit": desired_size_unit,
                "grayscale": grayscale,
            },
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
