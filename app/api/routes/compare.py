"""Compare two PDFs (semantic text diff + side-by-side view)."""
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_upload, validate_job_id, validate_file_size
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


def _get_compare_job(job_id: str) -> Job:
    try:
        validate_job_id(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.job_type != JobType.COMPARE_PDF:
        raise HTTPException(status_code=400, detail="Not a compare job")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Compare not ready yet")
    return job


@router.post("/compare")
async def compare_pdfs(files: List[UploadFile] = File(..., description="Two PDF files")):
    if len(files) != 2:
        raise HTTPException(status_code=400, detail="Exactly two PDFs required")

    for f in files:
        try:
            validate_upload(f)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_paths = []
    for i, f in enumerate(files):
        data = await f.read()
        try:
            validate_file_size(len(data))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        path = f"{base_path}/input_{i}.pdf"
        storage.save(path, data)
        input_paths.append(path)

    output_path = f"{base_path}/compare_result.zip"

    input_filenames = [f.filename for f in files]
    job = Job(
        job_id=job_id,
        job_type=JobType.COMPARE_PDF,
        status=JobStatus.PENDING,
        input_paths=input_paths,
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": input_filenames},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}


@router.get("/compare/{job_id}/left")
def compare_serve_left(job_id: str):
    """Serve the left (first) PDF for the compare viewer."""
    job = _get_compare_job(job_id)
    path = (job.params or {}).get("left_pdf")
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=404, detail="Left PDF not found")
    return FileResponse(path, media_type="application/pdf", filename="left.pdf")


@router.get("/compare/{job_id}/right")
def compare_serve_right(job_id: str):
    """Serve the right (second) PDF for the compare viewer."""
    job = _get_compare_job(job_id)
    path = (job.params or {}).get("right_pdf")
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=404, detail="Right PDF not found")
    return FileResponse(path, media_type="application/pdf", filename="right.pdf")


@router.get("/compare/{job_id}/report")
def compare_serve_report(job_id: str):
    """Return the change report JSON for the compare viewer."""
    job = _get_compare_job(job_id)
    path = (job.params or {}).get("report_path")
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    return report
