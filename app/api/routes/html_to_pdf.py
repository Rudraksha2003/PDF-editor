"""Convert HTML to PDF (file upload or URL)."""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, HttpUrl

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_file_size
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()

ALLOWED_HTML_TYPES = {"text/html", "application/xhtml+xml"}
ALLOWED_HTML_EXTENSIONS = (".html", ".htm")


class HtmlFromUrlBody(BaseModel):
    url: HttpUrl


@router.post("/html-to-pdf-from-url")
async def html_to_pdf_from_url(body: HtmlFromUrlBody):
    """Convert a webpage URL to PDF."""
    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    output_path = f"{base_path}/output.pdf"
    os.makedirs(base_path, exist_ok=True)

    job = Job(
        job_id=job_id,
        job_type=JobType.HTML_TO_PDF,
        status=JobStatus.PENDING,
        input_paths=[],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"url": str(body.url)},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}


@router.post("/html-to-pdf")
async def html_to_pdf(file: UploadFile = File(...)):
    fn = (file.filename or "").lower()
    ct = (file.content_type or "").strip().lower()
    if ct and ct not in ALLOWED_HTML_TYPES:
        raise HTTPException(status_code=400, detail="HTML file required (content type text/html).")
    if fn and not any(fn.endswith(ext) for ext in ALLOWED_HTML_EXTENSIONS):
        raise HTTPException(status_code=400, detail="HTML file required (.html or .htm).")
    if not fn and not ct:
        raise HTTPException(status_code=400, detail="HTML file required.")

    data = await file.read()
    try:
        validate_file_size(len(data))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input.html"
    output_path = f"{base_path}/output.pdf"

    storage.save(input_path, data)

    job = Job(
        job_id=job_id,
        job_type=JobType.HTML_TO_PDF,
        status=JobStatus.PENDING,
        input_paths=[input_path],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": [file.filename]},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}
