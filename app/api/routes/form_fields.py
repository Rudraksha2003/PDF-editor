"""List form fields in PDF (sync - returns JSON)."""
import io

from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.security.validators import validate_upload, validate_file_size

router = APIRouter()


@router.post("/form-fields")
async def form_fields(file: UploadFile = File(...)):
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
        fields = reader.get_fields()
        if fields is None:
            return {"fields": [], "count": 0}
        result = []
        for name, field in fields.items():
            result.append({
                "name": name,
                "type": str(type(field).__name__) if field else None,
            })
        return {"fields": result, "count": len(result)}
    except PyPdfError as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")
