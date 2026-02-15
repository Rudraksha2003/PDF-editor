"""Convert Office (Word, Excel, PowerPoint) to PDF. Requires LibreOffice."""
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_file_size
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()

# LibreOffice supports: doc, docx, xls, xlsx, ppt, pptx, odt, ods, odp
OFFICE_EXT = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp"}


@router.post("/office-to-pdf")
async def office_to_pdf(file: UploadFile = File(...)):
    fn = (file.filename or "").lower()
    if not any(fn.endswith(ext) for ext in OFFICE_EXT):
        raise HTTPException(
            status_code=400,
            detail="Office file required: .doc, .docx, .xls, .xlsx, .ppt, .pptx, .odt, .ods, .odp",
        )
    data = await file.read()
    try:
        validate_file_size(len(data))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input{fn[fn.rfind('.'):]}"
    output_path = f"{base_path}/output.pdf"

    storage.save(input_path, data)

    job = Job(
        job_id=job_id,
        job_type=JobType.OFFICE_TO_PDF,
        status=JobStatus.PENDING,
        input_paths=[input_path],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": [file.filename]},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}
