import asyncio
import io
import os
import shutil
import subprocess
import zipfile
from typing import Optional

from pypdf import PdfWriter, PdfReader
from pypdf.generic import FloatObject

from app.queue.in_memory import queue
from app.api.routes.jobs import JOB_STORE
from app.models.job import JobStatus, JobType
from app.utils.output_names import make_output_filename


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _find_tesseract_windows() -> Optional[str]:
    """Return path to tesseract.exe on Windows if installed in common locations."""
    if os.name != "nt":
        return None
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Tesseract-OCR", "tesseract.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Tesseract-OCR", "tesseract.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _find_libreoffice_windows() -> Optional[str]:
    """Return path to soffice.exe on Windows if installed in common locations."""
    if os.name != "nt":
        return None
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "LibreOffice", "program", "soffice.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "LibreOffice", "program", "soffice.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _run_libreoffice_convert(
    job, input_file: str, base_dir: str, fmt: str, base_name: str, expected: str,
) -> None:
    """Run LibreOffice --convert-to for PDF→Office (used when fmt is xlsx/pptx or pdf2docx failed)."""
    libreoffice_cmd = "libreoffice"
    libreoffice_cwd = None
    libreoffice_env = None
    if os.name == "nt":
        libreoffice_cmd = shutil.which("libreoffice") or os.environ.get("LIBREOFFICE_CMD") or _find_libreoffice_windows() or libreoffice_cmd
        if libreoffice_cmd == "libreoffice":
            libreoffice_cmd = shutil.which("soffice") or libreoffice_cmd
        if os.path.isfile(libreoffice_cmd):
            libreoffice_cwd = os.path.dirname(libreoffice_cmd)
            lo_parent = os.path.dirname(libreoffice_cwd)
            path_prepend = libreoffice_cwd + os.pathsep + lo_parent + os.pathsep + os.environ.get("PATH", "")
            libreoffice_env = {**os.environ, "PATH": path_prepend}
    export_filter = {"docx": "Office Open XML Text", "xlsx": "Calc MS Excel 2007 XML", "pptx": "Impress MS PowerPoint 2007 XML"}.get(fmt, "")
    convert_to = f"{fmt}:{export_filter}" if export_filter else fmt
    cmd = [
        libreoffice_cmd, "--headless",
        "--infilter=writer_pdf_import",
        "--convert-to", convert_to,
        "--outdir", base_dir, input_file,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
        cwd=libreoffice_cwd, env=libreoffice_env,
    )
    if result.returncode != 0:
        raise ValueError(f"LibreOffice failed: {result.stderr or result.stdout}")
    if os.path.isfile(expected) and expected != job.output_path:
        shutil.move(expected, job.output_path)


async def worker_loop():
    while True:
        job_id = await queue.get()
        job = JOB_STORE[job_id]

        try:
            job.status = JobStatus.PROCESSING
            params = job.params or {}

            # ---------- MERGE ----------
            if job.job_type == JobType.MERGE:
                writer = PdfWriter()
                for path in job.input_paths:
                    writer.append(path)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- SPLIT + ZIP ----------
            elif job.job_type == JobType.SPLIT:
                reader = PdfReader(job.input_paths[0])
                base_dir = os.path.dirname(job.output_path)
                zip_path = os.path.join(base_dir, "split_output.zip")
                split_files = []
                for i, page in enumerate(reader.pages, start=1):
                    w = PdfWriter()
                    w.add_page(page)
                    out_path = os.path.join(base_dir, f"split_page_{i}.pdf")
                    _ensure_dir(out_path)
                    with open(out_path, "wb") as f:
                        w.write(f)
                    split_files.append(out_path)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for fp in split_files:
                        zipf.write(fp, arcname=os.path.basename(fp))
                job.output_path = zip_path

            # ---------- ROTATE ----------
            elif job.job_type == JobType.ROTATE:
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                n = len(reader.pages)
                pages_to_rotate = set(params["pages"])
                bad = [p for p in pages_to_rotate if p < 1 or p > n]
                if bad:
                    raise ValueError(
                        f"Page number(s) {bad} do not exist. PDF has {n} page(s) (valid: 1–{n})."
                    )
                angle = params["angle"]
                for i, page in enumerate(reader.pages, start=1):
                    if i in pages_to_rotate:
                        page.rotate(angle)
                    writer.add_page(page)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- DELETE ----------
            elif job.job_type == JobType.DELETE:
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                n = len(reader.pages)
                delete_pages = set(params["pages"])
                bad = [p for p in delete_pages if p < 1 or p > n]
                if bad:
                    raise ValueError(
                        f"Page number(s) {bad} do not exist. PDF has {n} page(s) (valid: 1–{n})."
                    )
                for i, page in enumerate(reader.pages, start=1):
                    if i not in delete_pages:
                        writer.add_page(page)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- EXTRACT ----------
            elif job.job_type == JobType.EXTRACT:
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                page_list = params["pages"]
                n = len(reader.pages)
                bad = [p for p in page_list if p < 1 or p > n]
                if bad:
                    raise ValueError(
                        f"Page number(s) {bad} do not exist. PDF has {n} page(s) (valid: 1–{n})."
                    )
                for i in page_list:
                    writer.add_page(reader.pages[i - 1])
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- REORDER ----------
            elif job.job_type == JobType.REORDER:
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                order = params["order"]
                n = len(reader.pages)
                bad = [p for p in order if p < 1 or p > n]
                if bad:
                    raise ValueError(
                        f"Page number(s) {bad} do not exist. PDF has {n} page(s) (valid: 1–{n})."
                    )
                if len(order) != n or set(order) != set(range(1, n + 1)):
                    raise ValueError(
                        f"Order must list each page exactly once (1–{n}). Got {len(order)} page(s)."
                    )
                for i in order:
                    writer.add_page(reader.pages[i - 1])
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- CROP ----------
            elif job.job_type == JobType.CROP:
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                left = float(params.get("left", 0))
                bottom = float(params.get("bottom", 0))
                right = float(params.get("right", 0))
                top = float(params.get("top", 0))
                for page in reader.pages:
                    mb = page.mediabox
                    # Shrink mediabox by margins (crop)
                    mb.left = FloatObject(float(mb.left) + left)
                    mb.bottom = FloatObject(float(mb.bottom) + bottom)
                    mb.right = FloatObject(float(mb.right) - right)
                    mb.top = FloatObject(float(mb.top) - top)
                    writer.add_page(page)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- COMPRESS ----------
            elif job.job_type == JobType.COMPRESS:
                method = params.get("method", "quality")
                compression_level = int(params.get("compression_level", 5))
                grayscale = params.get("grayscale") in (True, "true", "True", "1", 1)
                desired_size = float(params.get("desired_size", 0))
                desired_size_unit = params.get("desired_size_unit", "MB")

                # 1) Default for everyone: use Ghostscript when available (real compression).
                #    Level 1-9 → prepress, printer, ebook, screen. Windows: gswin64c/gswin32c.
                gs_path = shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")
                if gs_path:
                    # Level 1-2=prepress, 3-4=printer, 5-6=ebook, 7-9=screen
                    if compression_level <= 2:
                        pdfsettings = "/prepress"
                    elif compression_level <= 4:
                        pdfsettings = "/printer"
                    elif compression_level <= 6:
                        pdfsettings = "/ebook"
                    else:
                        pdfsettings = "/screen"
                    gs_cmd = [
                        gs_path,
                        "-sDEVICE=pdfwrite",
                        "-dCompatibilityLevel=1.4",
                        "-dPDFSETTINGS=" + pdfsettings,
                        "-dNOPAUSE", "-dQUIET", "-dBATCH",
                        "-sOutputFile=" + job.output_path,
                        job.input_paths[0],
                    ]
                    if grayscale:
                        gs_cmd.insert(-1, "-dColorConversionStrategy=/Gray")
                        gs_cmd.insert(-1, "-dProcessColorModel=/DeviceGray")
                    result = subprocess.run(gs_cmd, capture_output=True, timeout=120)
                    if result.returncode == 0 and os.path.isfile(job.output_path):
                        pass  # success
                    else:
                        gs_path = None  # fall through to fallback
                if not gs_path:
                    # 2) Fallback when Ghostscript not installed: pikepdf or image path.
                    use_image_path = grayscale or method == "file_size" or (method == "quality" and compression_level >= 7)
                    if use_image_path:
                        try:
                            from pdf2image import convert_from_path
                            import img2pdf
                            from PIL import Image

                            if method == "file_size" and desired_size > 0:
                                quality = 40
                            else:
                                quality = min(95, 35 + compression_level * 6)

                            images = convert_from_path(job.input_paths[0], dpi=150)
                            base_dir = os.path.dirname(job.output_path)
                            img_paths = []
                            for i, img in enumerate(images):
                                if grayscale:
                                    img = img.convert("L").convert("RGB")
                                path = os.path.join(base_dir, f"page_{i:04d}.jpg")
                                img.save(path, "JPEG", quality=quality, optimize=True)
                                img_paths.append(path)
                            with open(job.output_path, "wb") as f:
                                f.write(img2pdf.convert(img_paths))
                            for p in img_paths:
                                try:
                                    os.remove(p)
                                except OSError:
                                    pass
                        except ImportError:
                            try:
                                import pikepdf
                                pdf = pikepdf.open(job.input_paths[0])
                                pdf.save(job.output_path, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
                                pdf.close()
                            except ImportError:
                                reader = PdfReader(job.input_paths[0])
                                writer = PdfWriter(clone_from=reader)
                                with open(job.output_path, "wb") as f:
                                    writer.write(f)
                    else:
                        # Level 1 (least compression): minimal rewrite so we don't inflate. No object streams.
                        try:
                            import pikepdf
                            pdf = pikepdf.open(job.input_paths[0])
                            if compression_level <= 1:
                                pdf.save(job.output_path, compress_streams=False, object_stream_mode=pikepdf.ObjectStreamMode.disable)
                            else:
                                pdf.save(job.output_path, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
                            pdf.close()
                        except ImportError:
                            reader = PdfReader(job.input_paths[0])
                            writer = PdfWriter(clone_from=reader)
                            with open(job.output_path, "wb") as f:
                                writer.write(f)

            # ---------- REPAIR ----------
            elif job.job_type == JobType.REPAIR:
                try:
                    import pikepdf
                    pdf = pikepdf.open(job.input_paths[0], allow_overwriting_input=True)
                    pdf.save(job.output_path)
                    pdf.close()
                except Exception:
                    reader = PdfReader(job.input_paths[0])
                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)
                    with open(job.output_path, "wb") as f:
                        writer.write(f)

            # ---------- ADD WATERMARK ----------
            elif job.job_type == JobType.ADD_WATERMARK:
                from reportlab.pdfgen import canvas
                text = params.get("text", "Watermark")
                opacity = float(params.get("opacity", 0.5))
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                base_font_size = 72
                for page in reader.pages:
                    w = float(page.mediabox.width)
                    h = float(page.mediabox.height)
                    diagonal = (w * w + h * h) ** 0.5
                    buf = io.BytesIO()
                    c = canvas.Canvas(buf, pagesize=(w, h))
                    c.setFillColorRGB(0.5, 0.5, 0.5, alpha=opacity)
                    c.setFont("Helvetica-Bold", base_font_size)
                    text_width_at_base = c.stringWidth(text)
                    if text_width_at_base > 0:
                        ratio = text_width_at_base / base_font_size
                        text_height_factor = 1.4
                        margin = 0.72
                        font_size = (margin * diagonal) / (ratio * ratio + text_height_factor * text_height_factor) ** 0.5
                    else:
                        font_size = base_font_size
                    c.setFont("Helvetica-Bold", font_size)
                    tw = c.stringWidth(text)
                    c.saveState()
                    c.translate(w / 2, h / 2)
                    c.rotate(45)
                    c.drawString(-tw / 2, -font_size * 0.35, text)
                    c.restoreState()
                    c.save()
                    buf.seek(0)
                    overlay_page = PdfReader(buf).pages[0]
                    page.merge_page(overlay_page)
                    writer.add_page(page)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- ADD PAGE NUMBERS ----------
            elif job.job_type == JobType.ADD_PAGE_NUMBERS:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter
                template = params.get("template", "Page {n} of {total}")
                position = params.get("position", "bottom_center")
                reader = PdfReader(job.input_paths[0])
                total = len(reader.pages)
                writer = PdfWriter()
                for idx, page in enumerate(reader.pages, start=1):
                    text = template.replace("{n}", str(idx)).replace("{total}", str(total))
                    buf = io.BytesIO()
                    c = canvas.Canvas(buf, pagesize=letter)
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.setFont("Helvetica", 10)
                    w, h = letter
                    if position == "bottom_center":
                        c.drawCentredString(w / 2, 36, text)
                    elif position == "bottom_right":
                        c.drawRightString(w - 72, 36, text)
                    elif position == "bottom_left":
                        c.drawString(72, 36, text)
                    elif position == "top_center":
                        c.drawCentredString(w / 2, h - 36, text)
                    elif position == "top_right":
                        c.drawRightString(w - 72, h - 36, text)
                    else:
                        c.drawCentredString(w / 2, 36, text)
                    c.save()
                    buf.seek(0)
                    overlay = PdfReader(buf).pages[0]
                    page.merge_page(overlay)
                    writer.add_page(page)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- PROTECT (encrypt) ----------
            elif job.job_type == JobType.PROTECT:
                password = params.get("password", "")
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter(clone_from=reader)
                writer.encrypt(password, algorithm="AES-256")
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- UNLOCK (decrypt) ----------
            elif job.job_type == JobType.UNLOCK:
                password = params.get("password", "")
                reader = PdfReader(job.input_paths[0])
                if reader.is_encrypted:
                    reader.decrypt(password)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- IMG TO PDF ----------
            elif job.job_type == JobType.IMG_TO_PDF:
                try:
                    import img2pdf
                    with open(job.output_path, "wb") as f:
                        f.write(img2pdf.convert(job.input_paths))
                except ImportError:
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib.utils import ImageReader
                    c = canvas.Canvas(job.output_path, pagesize=letter)
                    for path in job.input_paths:
                        img = ImageReader(path)
                        iw, ih = img.getSize()
                        c.setPageSize((iw, ih))
                        c.drawImage(path, 0, 0, width=iw, height=ih)
                        c.showPage()
                    c.save()

            # ---------- PDF TO IMG ----------
            elif job.job_type == JobType.PDF_TO_IMG:
                try:
                    from pdf2image import convert_from_path
                    img_format = params.get("format", "jpg")
                    images = convert_from_path(job.input_paths[0], dpi=150, fmt=img_format)
                    base_dir = os.path.dirname(job.output_path)
                    zip_path = os.path.join(base_dir, "images.zip")
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for i, img in enumerate(images, start=1):
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG" if img_format == "jpg" else "PNG", quality=90)
                            buf.seek(0)
                            ext = "jpg" if img_format == "jpg" else "png"
                            zipf.writestr(f"page_{i}.{ext}", buf.getvalue())
                    job.output_path = zip_path
                except ImportError:
                    raise ValueError(
                        "pdf2image is required for PDF to images. Install: pip install pdf2image. "
                        "On Windows you may need poppler: https://github.com/oschwartz10612/poppler-windows/releases"
                    )

            # ---------- OCR ----------
            elif job.job_type == JobType.OCR:
                try:
                    from pdf2image import convert_from_path
                    import pytesseract
                    # On Windows, Tesseract is often not in PATH; try common install locations
                    if os.name == "nt":
                        _tesseract_cmd = (
                            shutil.which("tesseract")
                            or (os.environ.get("TESSERACT_CMD"))
                            or _find_tesseract_windows()
                        )
                        if _tesseract_cmd:
                            pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd
                    images = convert_from_path(job.input_paths[0], dpi=300)
                    writer = PdfWriter()
                    for img in images:
                        pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, extension="pdf")
                        buf = io.BytesIO(pdf_bytes)
                        r = PdfReader(buf)
                        for p in r.pages:
                            writer.add_page(p)
                    with open(job.output_path, "wb") as f:
                        writer.write(f)
                except ImportError as e:
                    raise ValueError(
                        "OCR requires pdf2image and pytesseract, and Tesseract installed on the system. "
                        f"Install: pip install pdf2image pytesseract. Then install Tesseract. {e}"
                    )

            # ---------- PDF TO PDF/A ----------
            elif job.job_type == JobType.PDF_TO_PDFA:
                try:
                    import pikepdf
                    pdf = pikepdf.open(job.input_paths[0])
                    pdf.save(job.output_path, normalize_content=True)
                    pdf.close()
                except Exception:
                    r = PdfReader(job.input_paths[0])
                    w = PdfWriter(clone_from=r)
                    with open(job.output_path, "wb") as f:
                        w.write(f)

            # ---------- HTML TO PDF ----------
            elif job.job_type == JobType.HTML_TO_PDF:
                try:
                    # WeasyPrint on Windows needs Pango DLLs (e.g. from MSYS2). Prefer WEASYPRINT_DLL_DIRECTORIES.
                    if os.name == "nt" and "WEASYPRINT_DLL_DIRECTORIES" not in os.environ:
                        _dll_dir = os.path.join(os.environ.get("MSYS2_PATH", "C:\\msys64"), "mingw64", "bin")
                        if os.path.isdir(_dll_dir):
                            os.environ["WEASYPRINT_DLL_DIRECTORIES"] = _dll_dir
                    from weasyprint import HTML
                    url = (job.params or {}).get("url")
                    _ensure_dir(job.output_path)
                    if url:
                        HTML(url=url).write_pdf(job.output_path)
                    else:
                        HTML(filename=job.input_paths[0]).write_pdf(job.output_path)
                except ImportError:
                    raise ValueError("HTML to PDF requires weasyprint. Install: pip install weasyprint")

            # ---------- PDF TO TEXT ----------
            elif job.job_type == JobType.PDF_TO_TEXT:
                fmt = params.get("format", "text")
                try:
                    import pdfplumber
                    with pdfplumber.open(job.input_paths[0]) as pdf:
                        parts = []
                        for page in pdf.pages:
                            t = page.extract_text() or ""
                            if fmt == "markdown":
                                parts.append(f"---\n## Page {len(parts)+1}\n\n{t}")
                            else:
                                parts.append(t)
                        out = "\n\n".join(parts)
                    with open(job.output_path, "w", encoding="utf-8") as f:
                        f.write(out)
                except ImportError:
                    reader = PdfReader(job.input_paths[0])
                    parts = []
                    for i, page in enumerate(reader.pages):
                        t = page.extract_text() or ""
                        if fmt == "markdown":
                            parts.append(f"---\n## Page {i+1}\n\n{t}")
                        else:
                            parts.append(t)
                    with open(job.output_path, "w", encoding="utf-8") as f:
                        f.write("\n\n".join(parts))

            # ---------- SPLIT BY RANGE ----------
            elif job.job_type == JobType.SPLIT_BY_RANGE:
                reader = PdfReader(job.input_paths[0])
                base_dir = os.path.dirname(job.output_path)
                zip_path = os.path.join(base_dir, "split_output.zip")
                n = len(reader.pages)
                for a, b in params["ranges"]:
                    if a < 1 or b > n or a > b:
                        raise ValueError(
                            f"Range {a}-{b} is invalid. PDF has {n} page(s) (valid: 1–{n})."
                        )
                split_files = []
                for idx, (a, b) in enumerate(params["ranges"], start=1):
                    w = PdfWriter()
                    for i in range(a, b + 1):
                        w.add_page(reader.pages[i - 1])
                    out_path = os.path.join(base_dir, f"split_{idx}.pdf")
                    _ensure_dir(out_path)
                    with open(out_path, "wb") as f:
                        w.write(f)
                    split_files.append(out_path)
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for fp in split_files:
                        zipf.write(fp, arcname=os.path.basename(fp))
                job.output_path = zip_path

            # ---------- OFFICE TO PDF ----------
            elif job.job_type == JobType.OFFICE_TO_PDF:
                base_dir = os.path.dirname(os.path.abspath(job.output_path))
                input_file = os.path.abspath(job.input_paths[0])
                if not os.path.isfile(input_file):
                    input_file = os.path.realpath(job.input_paths[0])  # canonical path
                # LibreOffice: --headless --convert-to pdf --outdir <dir> <file>
                libreoffice_cmd = "libreoffice"
                libreoffice_cwd = None
                libreoffice_env = None
                if os.name == "nt":
                    libreoffice_cmd = shutil.which("libreoffice") or os.environ.get("LIBREOFFICE_CMD") or _find_libreoffice_windows() or libreoffice_cmd
                    if libreoffice_cmd == "libreoffice":
                        libreoffice_cmd = shutil.which("soffice") or libreoffice_cmd
                    if os.path.isfile(libreoffice_cmd):
                        libreoffice_cwd = os.path.dirname(libreoffice_cmd)
                        lo_parent = os.path.dirname(libreoffice_cwd)
                        path_prepend = libreoffice_cwd + os.pathsep + lo_parent + os.pathsep + os.environ.get("PATH", "")
                        libreoffice_env = {**os.environ, "PATH": path_prepend}
                cmd = [
                    libreoffice_cmd, "--headless", "--convert-to", "pdf",
                    "--outdir", base_dir, input_file,
                ]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120,
                    cwd=libreoffice_cwd, env=libreoffice_env,
                )
                if result.returncode != 0:
                    raise ValueError(f"LibreOffice failed: {result.stderr or result.stdout}")
                base_name = os.path.splitext(os.path.basename(job.input_paths[0]))[0]
                expected = os.path.join(base_dir, f"{base_name}.pdf")
                if os.path.isfile(expected) and expected != job.output_path:
                    shutil.move(expected, job.output_path)

            # ---------- PDF TO OFFICE ----------
            elif job.job_type == JobType.PDF_TO_OFFICE:
                fmt = params.get("format", "docx")
                base_dir = os.path.dirname(os.path.abspath(job.output_path))
                input_file = os.path.abspath(job.input_paths[0])
                if not os.path.isfile(input_file):
                    input_file = os.path.realpath(job.input_paths[0])  # canonical path
                base_name = os.path.splitext(os.path.basename(job.input_paths[0]))[0]
                expected = os.path.join(base_dir, f"{base_name}.{fmt}")

                # For DOCX, try pdf2docx first — produces native Word OOXML so Word opens it correctly (not blank)
                if fmt == "docx":
                    try:
                        from pdf2docx import Converter
                        cv = Converter(input_file)
                        cv.convert(job.output_path)
                        cv.close()
                        # pdf2docx wrote to job.output_path; nothing to move
                    except Exception:
                        # Fall back to LibreOffice (e.g. pdf2docx not installed or conversion failed)
                        _run_libreoffice_convert(
                            job, input_file, base_dir, fmt, base_name, expected,
                        )
                else:
                    _run_libreoffice_convert(
                        job, input_file, base_dir, fmt, base_name, expected,
                    )

            # ---------- FLATTEN ----------
            elif job.job_type == JobType.FLATTEN:
                import pikepdf

                def _strip_form_keep_links_only(pdf_doc):
                    """Remove AcroForm and all non-Link annotations so form fields are not clickable."""
                    if pikepdf.Name.AcroForm in pdf_doc.Root:
                        del pdf_doc.Root[pikepdf.Name.AcroForm]
                    for page in pdf_doc.pages:
                        annots = page.get(pikepdf.Name.Annots)
                        if annots is None:
                            continue
                        keep = []
                        for ref in list(annots):
                            try:
                                obj = ref.get_object() if hasattr(ref, "get_object") else ref
                                if obj.get(pikepdf.Name.Subtype) == pikepdf.Name.Link:
                                    keep.append(ref)
                            except Exception:
                                pass
                        page.obj[pikepdf.Name.Annots] = pikepdf.Array(keep)

                flatten_only_forms = params.get("flatten_only_forms") in (True, "true", "True", 1)
                try:
                    pdf = pikepdf.open(job.input_paths[0])
                    if flatten_only_forms:
                        # Flatten all (burns form widgets into content); then strip to only Link annots
                        pdf.generate_appearance_streams()
                        pdf.flatten_annotations(mode="all")
                        pdf.save(job.output_path)
                        pdf.close()
                        out = pikepdf.open(job.output_path)
                        _strip_form_keep_links_only(out)
                        out.save(job.output_path)
                        out.close()
                    else:
                        # Full flatten: burn all annotations, remove them
                        pdf.generate_appearance_streams()
                        pdf.flatten_annotations(mode="all")
                        for page in pdf.pages:
                            if "/Annots" in page:
                                del page["/Annots"]
                        pdf.save(job.output_path)
                        pdf.close()
                except Exception:
                    if flatten_only_forms:
                        # Flatten failed; still strip form so output has no clickable forms
                        try:
                            pdf = pikepdf.open(job.input_paths[0])
                            _strip_form_keep_links_only(pdf)
                            pdf.save(job.output_path)
                            pdf.close()
                        except Exception:
                            pass
                    if not os.path.exists(job.output_path):
                        reader = PdfReader(job.input_paths[0])
                        writer = PdfWriter()
                        for page in reader.pages:
                            writer.add_page(page)
                        with open(job.output_path, "wb") as f:
                            writer.write(f)

            # ---------- REMOVE BLANKS ----------
            elif job.job_type == JobType.REMOVE_BLANKS:
                reader = PdfReader(job.input_paths[0])
                try:
                    from pdf2image import convert_from_path
                    images = convert_from_path(job.input_paths[0], dpi=72)
                    writer = PdfWriter()
                    threshold = float(params.get("threshold", 0.01))
                    for i, img in enumerate(images):
                        if i >= len(reader.pages):
                            break
                        import statistics
                        px = list(img.getdata())
                        if len(px) == 0:
                            writer.add_page(reader.pages[i])
                            continue
                        if isinstance(px[0], tuple):
                            mean = sum(sum(p) for p in px) / (len(px) * len(px[0]))
                        else:
                            mean = statistics.mean(px)
                        if mean < 255 * (1 - threshold):
                            writer.add_page(reader.pages[i])
                    with open(job.output_path, "wb") as f:
                        writer.write(f)
                except ImportError:
                    writer = PdfWriter(clone_from=reader)
                    with open(job.output_path, "wb") as f:
                        writer.write(f)

            # ---------- ADD STAMP ----------
            elif job.job_type == JobType.ADD_STAMP:
                from reportlab.pdfgen import canvas
                from reportlab.lib.utils import ImageReader
                stamp_path = job.input_paths[1]
                position = params.get("position", "bottom_right")
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                img = ImageReader(stamp_path)
                iw, ih = img.getSize()
                scale = min(100 / iw, 100 / ih)
                iw, ih = iw * scale, ih * scale
                for page in reader.pages:
                    pw = float(page.mediabox.width)
                    ph = float(page.mediabox.height)
                    buf = io.BytesIO()
                    c = canvas.Canvas(buf, pagesize=(pw, ph))
                    # mask='auto' preserves PNG transparency so the stamp has no opaque background
                    if position == "bottom_right":
                        c.drawImage(stamp_path, pw - iw - 20, 20, width=iw, height=ih, mask="auto")
                    elif position == "bottom_left":
                        c.drawImage(stamp_path, 20, 20, width=iw, height=ih, mask="auto")
                    elif position == "top_right":
                        c.drawImage(stamp_path, pw - iw - 20, ph - ih - 20, width=iw, height=ih, mask="auto")
                    elif position == "top_left":
                        c.drawImage(stamp_path, 20, ph - ih - 20, width=iw, height=ih, mask="auto")
                    else:
                        c.drawImage(stamp_path, (pw - iw) / 2, (ph - ih) / 2, width=iw, height=ih, mask="auto")
                    c.save()
                    buf.seek(0)
                    overlay = PdfReader(buf).pages[0]
                    page.merge_page(overlay)
                    writer.add_page(page)
                with open(job.output_path, "wb") as f:
                    writer.write(f)

            # ---------- EXTRACT IMAGES ----------
            elif job.job_type == JobType.EXTRACT_IMAGES:
                reader = PdfReader(job.input_paths[0])
                base_dir = os.path.dirname(job.output_path)
                zip_path = os.path.join(base_dir, "images.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for page_num, page in enumerate(reader.pages):
                        try:
                            for img_fo in getattr(page, "images", []):
                                try:
                                    buf = io.BytesIO()
                                    if hasattr(img_fo, "image") and hasattr(img_fo.image, "save"):
                                        img_fo.image.save(buf, format="PNG")
                                    else:
                                        continue
                                    name = getattr(img_fo, "name", f"img_{page_num}").replace("/", "")
                                    zipf.writestr(f"page{page_num+1}_{name}.png", buf.getvalue())
                                except Exception:
                                    pass
                        except Exception:
                            pass
                job.output_path = zip_path

            # ---------- REDACT ----------
            # Prefer secure redaction: rasterize each page to an image so the text layer
            # is removed and redacted content cannot be copied. If poppler is not
            # installed (e.g. on Windows), fall back to overlay-only redaction.
            elif job.job_type == JobType.REDACT:
                import pdfplumber
                from reportlab.pdfgen import canvas

                phrases = params.get("phrases", [])
                reader = PdfReader(job.input_paths[0])
                writer = PdfWriter()
                use_secure_redaction = True

                try:
                    from pdf2image import convert_from_path
                except ImportError:
                    use_secure_redaction = False

                if use_secure_redaction:
                    try:
                        from reportlab.lib.utils import ImageReader as ReportLabImageReader
                        from PIL import ImageDraw

                        dpi = 150
                        scale = dpi / 72.0
                        with pdfplumber.open(job.input_paths[0]) as pdf:
                            for i, page in enumerate(pdf.pages):
                                images = convert_from_path(
                                    job.input_paths[0], dpi=dpi, first_page=i + 1, last_page=i + 1
                                )
                                if not images:
                                    continue
                                img = images[0]
                                if img.mode != "RGB":
                                    img = img.convert("RGB")

                                words = page.extract_words()
                                if words:
                                    draw = ImageDraw.Draw(img)
                                    for word in words:
                                        if any(phrase in (word.get("text") or "") for phrase in phrases):
                                            x0 = int(word["x0"] * scale)
                                            top = int(word["top"] * scale)
                                            x1 = int(word["x1"] * scale)
                                            bottom = int(word["bottom"] * scale)
                                            draw.rectangle([x0, top, x1, bottom], fill=(0, 0, 0), outline=(0, 0, 0))
                                img_buf = io.BytesIO()
                                img.save(img_buf, format="PNG")
                                img_buf.seek(0)

                                w_pt, h_pt = page.width, page.height
                                buf = io.BytesIO()
                                c = canvas.Canvas(buf, pagesize=(w_pt, h_pt))
                                c.drawImage(ReportLabImageReader(img_buf), 0, 0, width=w_pt, height=h_pt)
                                c.save()
                                buf.seek(0)
                                writer.add_page(PdfReader(buf).pages[0])

                        with open(job.output_path, "wb") as f:
                            writer.write(f)
                    except Exception as e:
                        err_msg = str(e).lower()
                        if "poppler" in err_msg or "page count" in err_msg or "pdfinfo" in err_msg:
                            use_secure_redaction = False
                        else:
                            raise

                if not use_secure_redaction:
                    # Fallback: overlay black rectangles only (text still in PDF, can be copied)
                    if job.params is None:
                        job.params = {}
                    job.params["redaction_warning"] = (
                        "Poppler is not installed. Redaction is visual only; text may still be copyable. "
                        "For secure redaction, install poppler (e.g. in Docker it is pre-installed)."
                    )
                    with pdfplumber.open(job.input_paths[0]) as pdf:
                        for i, page in enumerate(pdf.pages):
                            p = reader.pages[i]
                            words = page.extract_words()
                            if not words:
                                writer.add_page(p)
                                continue
                            buf = io.BytesIO()
                            w, h = page.width, page.height
                            c = canvas.Canvas(buf, pagesize=(w, h))
                            c.setFillColorRGB(0, 0, 0)
                            for word in words:
                                if any(phrase in (word.get("text") or "") for phrase in phrases):
                                    x0, top, x1, bottom = word["x0"], word["top"], word["x1"], word["bottom"]
                                    c.rect(x0, h - top - (bottom - top), x1 - x0, bottom - top, fill=1, stroke=0)
                            c.save()
                            buf.seek(0)
                            overlay = PdfReader(buf).pages[0]
                            p.merge_page(overlay)
                            writer.add_page(p)
                    with open(job.output_path, "wb") as f:
                        writer.write(f)

            # ---------- COMPARE PDF (semantic text diff + report + red/green highlights) ----------
            elif job.job_type == JobType.COMPARE_PDF:
                import difflib
                import json

                base_dir = os.path.dirname(job.output_path)
                left_pdf_path = os.path.join(base_dir, "left.pdf")
                right_pdf_path = os.path.join(base_dir, "right.pdf")
                report_json_path = os.path.join(base_dir, "report.json")
                report_txt_path = os.path.join(base_dir, "report.txt")

                try:
                    import pdfplumber
                    from reportlab.pdfgen import canvas
                except ImportError:
                    raise ValueError("Compare PDF requires pdfplumber and reportlab. Install: pip install pdfplumber reportlab")

                def extract_text_per_page(pdf_path):
                    with pdfplumber.open(pdf_path) as pdf:
                        return [(page.extract_text() or "").strip() for page in pdf.pages]

                def extract_words_per_page(pdf_path):
                    with pdfplumber.open(pdf_path) as pdf:
                        return [page.extract_words() or [] for page in pdf.pages]

                texts1 = extract_text_per_page(job.input_paths[0])
                texts2 = extract_text_per_page(job.input_paths[1])
                max_pages = max(len(texts1), len(texts2))

                changes = []
                for i in range(max_pages):
                    page_num = i + 1
                    t1 = texts1[i] if i < len(texts1) else ""
                    t2 = texts2[i] if i < len(texts2) else ""
                    lines1 = t1.splitlines() if t1 else []
                    lines2 = t2.splitlines() if t2 else []
                    matcher = difflib.SequenceMatcher(None, lines1, lines2)
                    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                        if tag == "replace":
                            old_blob = "\n".join(lines1[i1:i2])
                            new_blob = "\n".join(lines2[j1:j2])
                            if old_blob.strip():
                                changes.append({"page": page_num, "type": "remove", "text": old_blob})
                            if new_blob.strip():
                                changes.append({"page": page_num, "type": "add", "text": new_blob})
                        elif tag == "delete":
                            blob = "\n".join(lines1[i1:i2])
                            if blob.strip():
                                changes.append({"page": page_num, "type": "remove", "text": blob})
                        elif tag == "insert":
                            blob = "\n".join(lines2[j1:j2])
                            if blob.strip():
                                changes.append({"page": page_num, "type": "add", "text": blob})

                report = {
                    "changes": changes,
                    "summary": {"total": len(changes), "by_page": {}},
                }
                for c in changes:
                    p = str(c["page"])
                    report["summary"]["by_page"][p] = report["summary"]["by_page"].get(p, 0) + 1

                with open(report_json_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)

                with open(report_txt_path, "w", encoding="utf-8") as f:
                    f.write("Compare PDF — Change report\n")
                    f.write(f"Total changes: {len(changes)}\n\n")
                    for c in changes:
                        label = "Removed" if c["type"] == "remove" else "Added"
                        f.write(f"Page {c['page']} — {label}:\n{c['text']}\n\n")

                words1 = extract_words_per_page(job.input_paths[0])
                words2 = extract_words_per_page(job.input_paths[1])

                def merge_highlight_into_pdf(input_path, output_path, page_highlights):
                    """page_highlights[i] = list of (x0, top, x1, bottom, fill_rgb) for page i. We use fill_rgb for red or green."""
                    reader = PdfReader(input_path)
                    writer = PdfWriter()
                    for i, page in enumerate(reader.pages):
                        if i >= len(page_highlights) or not page_highlights[i]:
                            writer.add_page(page)
                            continue
                        red_rects = page_highlights[i].get("red", [])
                        green_rects = page_highlights[i].get("green", [])
                        if not red_rects and not green_rects:
                            writer.add_page(page)
                            continue
                        w = float(page.mediabox.width)
                        h = float(page.mediabox.height)
                        buf = io.BytesIO()
                        c = canvas.Canvas(buf, pagesize=(w, h))
                        if red_rects:
                            c.setFillColorRGB(1, 0, 0, alpha=0.35)
                            for (x0, top, x1, bottom) in red_rects:
                                y = h - bottom
                                c.rect(x0, y, max(0.5, x1 - x0), max(0.5, bottom - top), fill=1, stroke=0)
                        if green_rects:
                            c.setFillColorRGB(0, 0.7, 0, alpha=0.35)
                            for (x0, top, x1, bottom) in green_rects:
                                y = h - bottom
                                c.rect(x0, y, max(0.5, x1 - x0), max(0.5, bottom - top), fill=1, stroke=0)
                        c.save()
                        buf.seek(0)
                        overlay = PdfReader(buf).pages[0]
                        page.merge_page(overlay)
                        writer.add_page(page)
                    with open(output_path, "wb") as f:
                        writer.write(f)

                left_highlights = [{"red": [], "green": []} for _ in range(max_pages)]
                right_highlights = [{"red": [], "green": []} for _ in range(max_pages)]

                with pdfplumber.open(job.input_paths[0]) as pdf1, pdfplumber.open(job.input_paths[1]) as pdf2:
                    for i in range(max_pages):
                        page1 = pdf1.pages[i] if i < len(pdf1.pages) else None
                        page2 = pdf2.pages[i] if i < len(pdf2.pages) else None
                        words_left = (page1.extract_words() or []) if page1 else []
                        words_right = (page2.extract_words() or []) if page2 else []
                        texts_left = [w.get("text", "") for w in words_left]
                        texts_right = [w.get("text", "") for w in words_right]
                        matcher = difflib.SequenceMatcher(None, texts_left, texts_right)
                        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                            if tag in ("delete", "replace") and i1 < i2:
                                for k in range(i1, i2):
                                    w = words_left[k]
                                    r = (float(w["x0"]), float(w["top"]), float(w["x1"]), float(w["bottom"]))
                                    left_highlights[i]["red"].append(r)
                            if tag in ("insert", "replace") and j1 < j2:
                                for k in range(j1, j2):
                                    w = words_right[k]
                                    r = (float(w["x0"]), float(w["top"]), float(w["x1"]), float(w["bottom"]))
                                    right_highlights[i]["green"].append(r)

                merge_highlight_into_pdf(job.input_paths[0], left_pdf_path, left_highlights)
                merge_highlight_into_pdf(job.input_paths[1], right_pdf_path, right_highlights)

                zip_path = os.path.join(base_dir, "compare_result.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(report_json_path, "report.json")
                    zipf.write(report_txt_path, "report.txt")
                    zipf.write(left_pdf_path, "left.pdf")
                    zipf.write(right_pdf_path, "right.pdf")

                job.output_path = zip_path
                if job.params is None:
                    job.params = {}
                job.params["left_pdf"] = left_pdf_path
                job.params["right_pdf"] = right_pdf_path
                job.params["report_path"] = report_json_path

            # ---------- SIGN PDF ----------
            elif job.job_type == JobType.SIGN_PDF:
                try:
                    from endesive.pdf import cms
                    from cryptography.hazmat.primitives.serialization import load_pem_private_key
                    from cryptography.hazmat.backends import default_backend
                    from cryptography.x509 import load_pem_x509_certificate
                except ImportError:
                    raise ValueError(
                        "Sign PDF requires endesive and cryptography. Install: pip install endesive cryptography. "
                        "You need a PEM certificate and private key (or a PFX with key inside)."
                    )
                cert_path = job.input_paths[1]
                key_path = job.input_paths[2] if len(job.input_paths) > 2 else None
                with open(job.input_paths[0], "rb") as f:
                    data = f.read()

                key = None
                cert = None
                othercerts = []

                if key_path:
                    with open(cert_path, "rb") as fc:
                        cert = load_pem_x509_certificate(fc.read(), default_backend())
                    with open(key_path, "rb") as fk:
                        key = load_pem_private_key(fk.read(), password=None, backend=default_backend())
                else:
                    cert_data = open(cert_path, "rb").read()
                    try:
                        from cryptography.hazmat.primitives.serialization import pkcs12
                        p12 = pkcs12.load_key_and_certificates(
                            cert_data, None, default_backend()
                        )
                        key, cert, othercerts = p12[0], p12[1], (p12[2] or [])
                    except Exception:
                        cert = load_pem_x509_certificate(cert_data, default_backend())
                        raise ValueError(
                            "Private key is required. Provide a separate .pem key file, or use a PFX (.pfx) certificate that contains the key."
                        )

                import datetime
                date_str = datetime.datetime.utcnow().strftime("D:%Y%m%d%H%M%S+00'00'")
                udct = {
                    "sigflags": 3,
                    "sigflagsft": 132,
                    "sigpage": 0,
                    "signature": "Digitally signed",
                    "contact": "",
                    "location": "",
                    "signingdate": date_str,
                    "reason": "Signed with PDF Editor",
                }
                # endesive returns the incremental signature block; it must be appended to the original PDF
                signature_block = cms.sign(data, udct, key, cert, othercerts, "sha256")
                with open(job.output_path, "wb") as f:
                    f.write(data)
                    f.write(signature_block)

            # ---------- SANITIZE ----------
            elif job.job_type == JobType.SANITIZE:
                try:
                    import pikepdf
                    from pikepdf import Name

                    pdf = pikepdf.open(job.input_paths[0])
                    params = job.params or {}
                    remove_js = params.get("remove_javascript", True)
                    remove_embedded = params.get("remove_embedded_files", True)
                    remove_xmp = params.get("remove_xmp_metadata", False)
                    remove_docinfo = params.get("remove_document_metadata", False)
                    remove_links = params.get("remove_links", False)
                    remove_fonts = params.get("remove_fonts", False)

                    # --- JavaScript ---
                    if remove_js:
                        if Name.OpenAction in pdf.Root:
                            del pdf.Root.OpenAction
                        for page in pdf.pages:
                            if Name.JS in page:
                                del page[Name.JS]
                            if Name.AA in page:
                                del page[Name.AA]
                        if pdf.Root.get(Name.AcroForm):
                            af = pdf.Root.AcroForm
                            if Name.XFA in af:
                                del af[Name.XFA]
                            for field in af.get(Name.Fields, []):
                                if Name.AA in field:
                                    del field[Name.AA]
                                if Name.K in field and Name.AA in field.K:
                                    del field.K[Name.AA]
                        for page in pdf.pages:
                            for annot in page.get(Name.Annots, []):
                                if Name.AA in annot:
                                    del annot[Name.AA]
                                if Name.A in annot:
                                    a = annot.A
                                    if getattr(a, "get", None) and a.get(Name.S) == Name.JavaScript:
                                        del annot[Name.A]

                    # --- Embedded files ---
                    if remove_embedded and Name.Names in pdf.Root:
                        names = pdf.Root.Names
                        if Name.EmbeddedFiles in names:
                            del names[Name.EmbeddedFiles]

                    # --- XMP metadata ---
                    if remove_xmp and Name.Metadata in pdf.Root:
                        del pdf.Root[Name.Metadata]

                    # --- Document info (title, author, etc.) ---
                    if remove_docinfo:
                        try:
                            if hasattr(pdf, "docinfo") and pdf.docinfo is not None:
                                for key in list(pdf.docinfo.keys()):
                                    del pdf.docinfo[key]
                        except Exception:
                            pass
                        if Name.Info in pdf.trailer:
                            del pdf.trailer[Name.Info]

                    # --- Links (remove /A and /Dest from link annotations) ---
                    if remove_links:
                        for page in pdf.pages:
                            for annot in page.get(Name.Annots, []):
                                subtype = annot.get(Name.Subtype)
                                if subtype == Name.Link:
                                    for key in (Name.A, Name.Dest, Name.PA, Name.URI):
                                        if key in annot:
                                            del annot[key]

                    # --- Embedded fonts (remove font file streams from descriptors) ---
                    if remove_fonts:
                        fontfile_keys = (Name.FontFile, Name.FontFile2, Name.FontFile3)
                        for page in pdf.pages:
                            resources = page.get(Name.Resources)
                            if resources is None:
                                continue
                            fonts = resources.get(Name.Font)
                            if fonts is None:
                                continue
                            for fname in list(fonts.keys()):
                                font = fonts[fname]
                                if Name.FontDescriptor not in font:
                                    continue
                                fd = font.FontDescriptor
                                for k in fontfile_keys:
                                    if k in fd:
                                        del fd[k]

                    pdf.remove_unreferenced_resources()
                    pdf.save(job.output_path, compress_streams=True)
                    pdf.close()
                except Exception:
                    reader = PdfReader(job.input_paths[0])
                    writer = PdfWriter()
                    for page in reader.pages:
                        writer.add_page(page)
                    with open(job.output_path, "wb") as f:
                        writer.write(f)

            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")

            input_filenames = (job.params or {}).get("input_filenames")
            job.output_filename = make_output_filename(
                job.job_type, input_filenames, job.output_path
            )
            job.status = JobStatus.COMPLETED

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
