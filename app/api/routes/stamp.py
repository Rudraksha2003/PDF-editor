"""Add stamp (image overlay) to every page."""
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_upload, validate_upload_image, validate_file_size
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/stamp")
async def add_stamp(
    file: UploadFile = File(..., description="PDF file"),
    stamp: UploadFile = File(..., description="Image to stamp (PNG/JPG)"),
    position: str = Form("bottom_right", description="bottom_right, bottom_left, top_right, top_left, center"),
):
    try:
        validate_upload(file)
        validate_upload_image(stamp)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    pdf_data = await file.read()
    stamp_data = await stamp.read()
    try:
        validate_file_size(len(pdf_data))
        validate_file_size(len(stamp_data))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input.pdf"
    output_path = f"{base_path}/stamped.pdf"

    storage.save(input_path, pdf_data)
    ext = "jpg" if stamp.content_type == "image/jpeg" else "png"
    storage.save(f"{base_path}/stamp.{ext}", stamp_data)

    job = Job(
        job_id=job_id,
        job_type=JobType.ADD_STAMP,
        status=JobStatus.PENDING,
        input_paths=[input_path, f"{base_path}/stamp.{ext}"],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"position": position, "input_filenames": [file.filename]},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}
