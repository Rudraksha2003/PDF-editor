import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import (
    upload,
    jobs,
    download,
    health,
    merge,
    split,
    split_by_range,
    rotate,
    delete,
    extract,
    reorder,
    crop,
    compress,
    repair,
    ocr,
    watermark,
    page_numbers,
    stamp,
    flatten,
    remove_blanks,
    extract_images,
    edit_pdf,
    protect,
    unlock,
    redact,
    sign_pdf,
    sanitize,
    compare,
    img_to_pdf,
    pdf_to_img,
    pdf_to_pdfa,
    pdf_to_text,
    html_to_pdf,
    office_to_pdf,
    pdf_to_office,
    document_info,
    form_fields,
    validate_signature,
)
from app.workers.worker import worker_loop

app = FastAPI(
    title="PDF Platform API",
    version="0.1",
    description="PDF editing, conversion, and analysis API. Upload PDFs, run jobs, download results.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(upload.router, tags=["Upload & Jobs"])
app.include_router(jobs.router, tags=["Upload & Jobs"])
app.include_router(download.router, tags=["Upload & Jobs"])
app.include_router(merge.router, tags=["Organize"])
app.include_router(split.router, tags=["Organize"])
app.include_router(split_by_range.router, tags=["Organize"])
app.include_router(delete.router, tags=["Organize"])
app.include_router(extract.router, tags=["Organize"])
app.include_router(reorder.router, tags=["Organize"])
app.include_router(compress.router, tags=["Optimize"])
app.include_router(repair.router, tags=["Optimize"])
app.include_router(ocr.router, tags=["Optimize"])
app.include_router(img_to_pdf.router, tags=["Convert"])
app.include_router(pdf_to_img.router, tags=["Convert"])
app.include_router(pdf_to_pdfa.router, tags=["Convert"])
app.include_router(pdf_to_text.router, tags=["Convert"])
app.include_router(html_to_pdf.router, tags=["Convert"])
app.include_router(office_to_pdf.router, tags=["Convert"])
app.include_router(pdf_to_office.router, tags=["Convert"])
app.include_router(rotate.router, tags=["Edit"])
app.include_router(crop.router, tags=["Edit"])
app.include_router(page_numbers.router, tags=["Edit"])
app.include_router(watermark.router, tags=["Edit"])
app.include_router(stamp.router, tags=["Edit"])
app.include_router(flatten.router, tags=["Edit"])
app.include_router(remove_blanks.router, tags=["Edit"])
app.include_router(extract_images.router, tags=["Edit"])
app.include_router(edit_pdf.router, tags=["Edit"])
app.include_router(protect.router, tags=["Security"])
app.include_router(unlock.router, tags=["Security"])
app.include_router(redact.router, tags=["Security"])
app.include_router(sign_pdf.router, tags=["Security"])
app.include_router(sanitize.router, tags=["Security"])
app.include_router(compare.router, tags=["Security"])
app.include_router(document_info.router, tags=["Analysis"])
app.include_router(form_fields.router, tags=["Analysis"])
app.include_router(validate_signature.router, tags=["Analysis"])

# Frontend: serve index.html at / and static assets under /static
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return {"message": "Frontend not found. Run from project root."}
    return FileResponse(index_path)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker_loop())
