"""Get PDF document info (sync - returns JSON)."""
import io

from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.security.validators import validate_upload, validate_file_size

router = APIRouter()


@router.post("/document-info")
async def document_info(file: UploadFile = File(...)):
    try:
        validate_upload(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = await file.read()
    try:
        validate_file_size(len(data))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        reader = PdfReader(io.BytesIO(data))
        meta = reader.metadata
        info = {
            "page_count": len(reader.pages),
            "metadata": {
                "title": getattr(meta, "title", None) or (meta.get("/Title") if meta else None),
                "author": getattr(meta, "author", None) or (meta.get("/Author") if meta else None),
                "subject": getattr(meta, "subject", None) or (meta.get("/Subject") if meta else None),
                "creator": getattr(meta, "creator", None) or (meta.get("/Creator") if meta else None),
                "producer": getattr(meta, "producer", None) or (meta.get("/Producer") if meta else None),
                "creation_date": str(meta.get("/CreationDate")) if meta else None,
                "modification_date": str(meta.get("/ModDate")) if meta else None,
            },
            "is_encrypted": reader.is_encrypted,
        }
        # Flatten metadata dict if it's a dict-like object
        if hasattr(meta, "get") and meta:
            info["metadata_raw"] = {str(k): str(v) for k, v in meta.items()}
        return info
    except PyPdfError as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")
