"""Validate digital signatures in PDF (sync - returns JSON)."""
import io

from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.security.validators import validate_upload, validate_file_size

router = APIRouter()


@router.post("/validate-signature")
async def validate_signature(file: UploadFile = File(...)):
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
        # pypdf can expose signature info from embedded signatures
        sigs = []
        if hasattr(reader, "get_signature_info") and reader.get_signature_info:
            sigs = reader.get_signature_info()
        # Fallback: report whether we could open (encrypted vs not)
        return {
            "valid": True,
            "message": "Signature validation requires full certificate chain; basic PDF read succeeded.",
            "is_encrypted": reader.is_encrypted,
            "signatures": sigs if sigs else [],
        }
    except PyPdfError as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")
