"""Convert one or more images to a single PDF."""
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_upload_image, validate_file_size
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/img-to-pdf")
async def images_to_pdf(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="At least one image required")

    for file in files:
        try:
            validate_upload_image(file)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_paths = []

    for idx, file in enumerate(files):
        data = await file.read()
        try:
            validate_file_size(len(data))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        ext = "jpg" if file.content_type == "image/jpeg" else "png"
        path = f"{base_path}/img_{idx}.{ext}"
        storage.save(path, data)
        input_paths.append(path)

    output_path = f"{base_path}/output.pdf"

    input_filenames = [f.filename for f in files]
    job = Job(
        job_id=job_id,
        job_type=JobType.IMG_TO_PDF,
        status=JobStatus.PENDING,
        input_paths=input_paths,
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": input_filenames},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}
