from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.security.validators import validate_page_numbers
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/rotate")
async def rotate_pdf(
    file: UploadFile = File(...),
    pages: str = Form(..., description="Comma-separated page numbers, e.g. 1,3,5"),
    angle: int = Form(..., description="Rotation angle: 90, 180, or 270"),
):
    if angle not in (90, 180, 270):
        raise HTTPException(status_code=400, detail="Angle must be 90, 180, or 270")
    try:
        page_list = [int(p.strip()) for p in pages.split(",") if p.strip()]
        validate_page_numbers(page_list, allow_empty=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.ROTATE,
            "rotated.pdf",
            {"pages": page_list, "angle": angle, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
