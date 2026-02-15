"""Sign PDF with a certificate (digital signature)."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_upload, validate_file_size
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()

@router.post("/sign")
async def sign_pdf(
    file: UploadFile = File(..., description="PDF to sign"),
    cert: UploadFile = File(..., description="Certificate file (.pem or .crt)"),
    key: Optional[UploadFile] = File(None, description="Private key (.pem). If not provided, cert may be PFX with key inside."),
):
    try:
        validate_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cert_fn = (cert.filename or "").lower()
    if cert_fn and not any(cert_fn.endswith(ext) for ext in (".pem", ".crt", ".pfx")):
        raise HTTPException(
            status_code=400,
            detail="Certificate must be a .pem, .crt, or .pfx file.",
        )
    if key:
        key_fn = (key.filename or "").lower()
        if key_fn and not key_fn.endswith(".pem"):
            raise HTTPException(status_code=400, detail="Private key must be a .pem file.")

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input.pdf"
    cert_path = f"{base_path}/cert.pem"
    key_path = f"{base_path}/key.pem" if key else None
    output_path = f"{base_path}/signed.pdf"

    pdf_data = await file.read()
    cert_data = await cert.read()
    try:
        validate_file_size(len(pdf_data))
        validate_file_size(len(cert_data))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    storage.save(input_path, pdf_data)
    storage.save(cert_path, cert_data)

    input_paths = [input_path, cert_path]
    if key:
        key_data = await key.read()
        try:
            validate_file_size(len(key_data))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        storage.save(key_path, key_data)
        input_paths.append(key_path)

    input_filenames = [file.filename]
    job = Job(
        job_id=job_id,
        job_type=JobType.SIGN_PDF,
        status=JobStatus.PENDING,
        input_paths=input_paths,
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": input_filenames},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}
