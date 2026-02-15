"""Shared helpers for PDF job routes: validation, job creation, and file size checks."""
import uuid
from datetime import datetime

from fastapi import UploadFile

from app.api.routes.jobs import JOB_STORE
from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.security.validators import (
    validate_file_size,
    validate_pdf_limits,
    validate_upload,
)
from app.storage.local import LocalStorage


async def create_single_file_pdf_job(
    file: UploadFile,
    job_type: JobType,
    output_filename: str,
    params: dict,
    storage: LocalStorage,
    *,
    validate_pdf_limits_after_save: bool = True,
) -> str:
    """
    Validate PDF upload (type + size), save to job dir, optionally check page limit,
    create job, register, enqueue, and return job_id.
    """
    validate_upload(file)
    data = await file.read()
    validate_file_size(len(data))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input.pdf"
    output_path = f"{base_path}/{output_filename}"

    storage.save(input_path, data)

    if validate_pdf_limits_after_save:
        validate_pdf_limits(input_path)

    job = Job(
        job_id=job_id,
        job_type=job_type,
        status=JobStatus.PENDING,
        input_paths=[input_path],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params=params,
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return job_id
