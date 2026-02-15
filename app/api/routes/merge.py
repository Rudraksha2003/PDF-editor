import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_upload, validate_file_size, validate_pdf_limits
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


@router.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least two PDFs required")

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_paths = []

    for idx, file in enumerate(files):
        try:
            validate_upload(file)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        data = await file.read()
        try:
            validate_file_size(len(data))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        input_path = f"{base_path}/input_{idx}.pdf"
        storage.save(input_path, data)
        try:
            validate_pdf_limits(input_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        input_paths.append(input_path)

    output_path = f"{base_path}/merged.pdf"

    input_filenames = [f.filename for f in files]
    job = Job(
        job_id=job_id,
        job_type=JobType.MERGE,
        status=JobStatus.PENDING,
        input_paths=input_paths,
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": input_filenames},
    )

    JOB_STORE[job_id] = job
    await queue.put(job_id)

    return {"job_id": job_id}
