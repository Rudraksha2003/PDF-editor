from fastapi import APIRouter, HTTPException

from app.models.job import Job
from app.security.validators import validate_job_id

router = APIRouter()
JOB_STORE: dict[str, Job] = {}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    try:
        validate_job_id(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found")
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
