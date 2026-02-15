# PDF Editor

A web app to edit, convert, and manage PDFs. Merge, split, rotate, compress, protect, convert to/from Office and images, add watermarks, run OCR, and more — all through a simple API and UI.

---

## Quick start

```bash
# Clone and enter the project
cd pdf-editor

# Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** for the UI, or **http://127.0.0.1:8000/docs** for the API.

---

## What you can do

| Category | Tools |
|----------|--------|
| **Organize** | Merge, split, split by range, delete pages, extract pages, reorder |
| **Optimize** | Compress, repair, **OCR** (make scanned PDFs searchable) |
| **Convert** | Images → PDF, PDF → images, PDF → PDF/A, PDF → text, HTML → PDF, Office → PDF, PDF → Office |
| **Edit** | Rotate, crop, page numbers, watermark, stamp, flatten, remove blank pages, extract images, **edit text** (extract spans, replace in place with same font/size) |
| **Security** | Protect (password), unlock, redact, sign, sanitize, compare |

Most features work with only Python and the packages in `requirements.txt`. A few tools need extra system software (see below).

---

## Optional: system dependencies

These are **only needed for specific tools**. The app runs without them; those tools will fail until you install the right dependency.

### OCR PDF (make scanned PDFs searchable)

**OCR** = *Optical Character Recognition*: it reads text from scanned PDFs (images of pages) so you can search and select the text. This tool needs **Tesseract** on your system; the app calls the Tesseract executable.

#### Windows

1. **Install Tesseract**  
   Download: [tesseract-ocr-w64-setup](https://github.com/UB-Mannheim/tesseract/wiki) (or search “tesseract windows”).  
   Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`.

2. **Optional:** Add Tesseract to PATH, or set `TESSERACT_CMD` to the full path of `tesseract.exe`.

#### macOS

```bash
brew install tesseract
```

#### Linux

```bash
# Debian/Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-eng

# Fedora
sudo dnf install tesseract
```

---

### HTML → PDF (WeasyPrint)

The **HTML → PDF** tool uses **WeasyPrint**, which needs **Pango** (and its DLLs on Windows). If you see `cannot load library '...libgobject-2.0-0.dll'`, Pango is missing or not on the right path.

#### Windows

1. Install [MSYS2](https://www.msys2.org/).
2. In MSYS2: `pacman -S mingw-w64-x86_64-pango`
3. Add `C:\msys64\mingw64\bin` to PATH, or set:
   ```text
   WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
   ```

#### macOS / Linux

- **macOS:** `brew install weasyprint`
- **Linux:** Install `weasyprint` or Pango + related packages, then `pip install weasyprint`

More: [WeasyPrint first steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation).

---

### Office → PDF / PDF → Office (LibreOffice)

**Office → PDF** and **PDF → Office** use **LibreOffice** in headless mode. If you see *"The system cannot find the file specified"*, install LibreOffice.

#### Windows

1. Install from [libreoffice.org](https://www.libreoffice.org/download/download/).  
   Default: `C:\Program Files\LibreOffice\program\soffice.exe`.
2. Optional: set `LIBREOFFICE_CMD` to the path of `soffice.exe` if you use a different install path.

#### macOS / Linux

- **macOS:** `brew install libreoffice`
- **Linux:** Install the `libreoffice` (or `libreoffice-core`) package.

---

### PDF to image (used by OCR)

Converting PDF pages to images (e.g. for OCR) uses **Poppler**. On Windows, if you get errors about `pdftoppm` or poppler, install [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add its `bin` folder to PATH.

---

## Deployment

- **Environment variables:** See `.env.example` for optional config (paths for Tesseract, LibreOffice, job storage). Copy to `.env` for local use only — **never commit `.env` or any file containing secrets to Git.**
- **Docker:** Use the included `Dockerfile` for containerized deployment (e.g. Oracle Cloud, any VPS).
