from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.routes.jobs import JOB_STORE
from app.models.job import JobStatus
from app.security.validators import validate_job_id

router = APIRouter()

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".txt": "text/plain",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

def _get_completed_job_response(job_id: str, disposition: str = "attachment"):
    try:
        validate_job_id(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOB_STORE.get(job_id)
    if not job or job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="File not ready")
    filename = job.output_filename or "result.pdf"
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ".pdf"
    media_type = MEDIA_TYPES.get(ext, "application/octet-stream")
    content_disp = f'{disposition}; filename="{quote(filename)}"'
    return FileResponse(
        job.output_path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": content_disp},
    )


@router.get("/download/{job_id}")
def download(job_id: str):
    return _get_completed_job_response(job_id, disposition="attachment")


@router.get("/preview/{job_id}")
def preview(job_id: str):
    """Serve the result file for in-browser display (e.g. in an iframe)."""
    return _get_completed_job_response(job_id, disposition="inline")
