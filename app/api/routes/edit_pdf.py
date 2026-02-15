"""Edit PDF: extract text spans (with font/size/position) and replace text in place."""
import json
import os
import shutil
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.models.job import Job, JobStatus, JobType
from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.security.validators import validate_file_size, validate_pdf_limits, validate_job_id
from app.storage.local import LocalStorage

router = APIRouter()
storage = LocalStorage()


def _validate_replacements(replacements: list) -> None:
    """Raise ValueError if replacements format is invalid."""
    if not replacements:
        raise ValueError("replacements must be a non-empty list")
    for i, r in enumerate(replacements):
        if not isinstance(r, dict):
            raise ValueError(f"replacements[{i}] must be an object")
        if "old_text" not in r or "new_text" not in r:
            raise ValueError(f"replacements[{i}] must have 'old_text' and 'new_text'")
        if not isinstance(r.get("old_text"), str) or not isinstance(r.get("new_text"), str):
            raise ValueError(f"replacements[{i}] old_text and new_text must be strings")
        if "page_index" in r and r["page_index"] is not None:
            if not isinstance(r["page_index"], int) or r["page_index"] < 0:
                raise ValueError(f"replacements[{i}] page_index must be a non-negative integer")
        if "bbox" in r and r["bbox"] is not None:
            if not isinstance(r["bbox"], (list, tuple)) or len(r["bbox"]) != 4:
                raise ValueError(f"replacements[{i}] bbox must be a list of 4 numbers")
            if not all(isinstance(x, (int, float)) for x in r["bbox"]):
                raise ValueError(f"replacements[{i}] bbox values must be numbers")


def _ensure_pdf_bytes(data: bytes) -> None:
    """Raise ValueError if data does not look like a PDF (magic bytes)."""
    if len(data) < 8 or not data.startswith(b"%PDF"):
        raise ValueError("File does not appear to be a PDF.")

@router.post("/edit-pdf/extract")
async def edit_pdf_extract(file: UploadFile = File(...)):
    """
    Extract editable text spans from a PDF (digital text only).
    Returns a job_id; when completed, download the result to get a JSON file
    with spans: text, bbox, font_name, font_size, color, page_index.
    """
    data = await file.read()
    validate_file_size(len(data))
    try:
        _ensure_pdf_bytes(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input.pdf"
    output_path = f"{base_path}/extract.json"

    storage.save(input_path, data)
    try:
        validate_pdf_limits(input_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job = Job(
        job_id=job_id,
        job_type=JobType.EDIT_PDF_EXTRACT,
        status=JobStatus.PENDING,
        input_paths=[input_path],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": [file.filename or "document.pdf"]},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}


@router.post("/edit-pdf/replace")
async def edit_pdf_replace(
    file: UploadFile = File(...),
    replacements: str = Form(..., description='JSON array of {"old_text": "...", "new_text": "..."}'),
):
    """
    Replace text in a PDF while preserving font and size where possible.
    replacements: JSON array, e.g. [{"old_text": "Hello", "new_text": "Hi"}].
    All occurrences of each old_text are replaced. Returns job_id; result is the edited PDF.
    """
    data = await file.read()
    validate_file_size(len(data))
    try:
        _ensure_pdf_bytes(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        repl_list = json.loads(replacements)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON for replacements: {e}")

    try:
        _validate_replacements(repl_list)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input.pdf"
    output_path = f"{base_path}/output.pdf"

    storage.save(input_path, data)
    try:
        validate_pdf_limits(input_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job = Job(
        job_id=job_id,
        job_type=JobType.EDIT_PDF_REPLACE,
        status=JobStatus.PENDING,
        input_paths=[input_path],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={
            "input_filenames": [file.filename or "document.pdf"],
            "replacements": repl_list,
        },
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}


@router.post("/edit-pdf/prepare")
async def edit_pdf_prepare(file: UploadFile = File(...)):
    """
    Prepare a PDF for editing: extract text spans; if none found, run OCR automatically
    then extract. Returns job_id; when completed, use GET /edit-pdf/jobs/{job_id}/extract
    for spans and GET /download/{job_id} for the editable PDF.
    """
    data = await file.read()
    validate_file_size(len(data))
    try:
        _ensure_pdf_bytes(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{job_id}"
    input_path = f"{base_path}/input.pdf"
    output_path = f"{base_path}/output.pdf"

    storage.save(input_path, data)
    try:
        validate_pdf_limits(input_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job = Job(
        job_id=job_id,
        job_type=JobType.EDIT_PDF_PREPARE,
        status=JobStatus.PENDING,
        input_paths=[input_path],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={"input_filenames": [file.filename or "document.pdf"]},
    )
    JOB_STORE[job_id] = job
    await queue.put(job_id)
    return {"job_id": job_id}


@router.get("/edit-pdf/jobs/{job_id}/extract")
async def get_edit_pdf_extract(job_id: str):
    """Return the extract.json (spans) for a completed edit-pdf prepare job."""
    try:
        validate_job_id(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.job_type != JobType.EDIT_PDF_PREPARE:
        raise HTTPException(status_code=400, detail="Not an edit-pdf prepare job")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    extract_path = os.path.join(os.path.dirname(job.output_path), "extract.json")
    if not os.path.isfile(extract_path):
        raise HTTPException(status_code=404, detail="Extract data not found")
    with open(extract_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@router.post("/edit-pdf/apply-edits")
async def edit_pdf_apply_edits(
    prepare_job_id: str = Form(...),
    replacements: str = Form(..., description='JSON array of {"old_text": "...", "new_text": "..."}'),
):
    """
    Apply edits (replacements) to a prepared PDF. Uses the prepare job's output as input.
    Returns a new job_id; when completed, download the edited PDF from /download/{job_id}.
    """
    try:
        validate_job_id(prepare_job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Prepare job not found")
    job = JOB_STORE.get(prepare_job_id)
    if not job or job.job_type != JobType.EDIT_PDF_PREPARE or job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Invalid or incomplete prepare job")
    if not os.path.isfile(job.output_path):
        raise HTTPException(status_code=400, detail="Prepared PDF no longer available")

    try:
        repl_list = json.loads(replacements)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON for replacements: {e}")
    try:
        _validate_replacements(repl_list)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    new_job_id = str(uuid.uuid4())
    base_path = f"/tmp/pdf-jobs/{new_job_id}"
    input_path = f"{base_path}/input.pdf"
    output_path = f"{base_path}/output.pdf"
    os.makedirs(base_path, exist_ok=True)
    shutil.copy(job.output_path, input_path)

    new_job = Job(
        job_id=new_job_id,
        job_type=JobType.EDIT_PDF_REPLACE,
        status=JobStatus.PENDING,
        input_paths=[input_path],
        output_path=output_path,
        created_at=datetime.utcnow(),
        params={
            "input_filenames": (job.params or {}).get("input_filenames", ["document.pdf"]),
            "replacements": repl_list,
        },
    )
    JOB_STORE[new_job_id] = new_job
    await queue.put(new_job_id)
    return {"job_id": new_job_id}
