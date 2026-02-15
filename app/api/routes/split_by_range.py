"""Split PDF by page ranges (e.g. 1-3, 4-6, 7)."""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import JobType
from app.api.routes.common import create_single_file_pdf_job
from app.security.validators import validate_page_numbers
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/split-by-range")
async def split_by_range(
    file: UploadFile = File(...),
    ranges: str = Form(..., description="Comma-separated ranges: 1-3,4-6,7"),
):
    try:
        range_list = []
        for part in ranges.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                a, b = int(a.strip()), int(b.strip())
                if a > b:
                    raise ValueError(f"Invalid range {a}-{b}: start must be ≤ end")
                range_list.append((a, b))
            else:
                n = int(part)
                range_list.append((n, n))
        if not range_list:
            raise ValueError("At least one range required")
        all_pages = []
        for a, b in range_list:
            all_pages.extend(range(a, b + 1))
        validate_page_numbers(all_pages, allow_empty=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        job_id = await create_single_file_pdf_job(
            file,
            JobType.SPLIT_BY_RANGE,
            "split_1.pdf",
            {"ranges": range_list, "input_filenames": [file.filename]},
            storage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}
