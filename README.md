# PDF Editor

## OCR PDF

The **OCR PDF** tool needs the **Tesseract** engine installed on your system (the Python package `pytesseract` only calls the Tesseract executable).

### Windows

1. **Install Tesseract**
   - Download the installer: [tesseract-ocr-w64-setup](https://github.com/UB-Mannheim/tesseract/wiki) (or search "tesseract windows" for the official installers).
   - Run the installer and complete the setup.
   - Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`.

2. **Optional: add to PATH**
   - If you don’t add Tesseract to PATH, this app will still try to use it from the default install path above.

3. **Optional: custom path**
   - Set the environment variable `TESSERACT_CMD` to the full path of `tesseract.exe` if you installed it somewhere else.

### macOS

```bash
brew install tesseract
```

### Linux

```bash
# Debian/Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-eng

# Fedora
sudo dnf install tesseract
```

---

## HTML → PDF (WeasyPrint)

The **HTML → PDF** tool uses **WeasyPrint**, which needs **Pango** (and its DLLs) on Windows. If you see an error like `cannot load library '...libgobject-2.0-0.dll': error 0x7e`, Pango is missing or the wrong DLL path is used.

### Windows

1. **Install MSYS2**  
   Download and install from [msys2.org](https://www.msys2.org/) (keep default options).

2. **Install Pango**  
   Open **MSYS2** (the “MSYS2 MSYS” shortcut), then run:
   ```bash
   pacman -S mingw-w64-x86_64-pango
   ```
   Accept the dependencies, then close MSYS2.

3. **Tell WeasyPrint where the DLLs are**  
   Add this folder to your **PATH** (see “What to put in PATH” above):
   ```text
   C:\msys64\mingw64\bin
   ```
   If you installed MSYS2 somewhere else, use that path plus `\mingw64\bin`.

   **Or** set this environment variable (no restart of the app needed if you set it in the same terminal before running):
   ```text
   WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin
   ```
   This app will also use that folder automatically if it exists and the variable is not already set.

### macOS / Linux

- **macOS:** `brew install weasyprint` (or install Pango and then `pip install weasyprint`).  
- **Linux:** Install the `weasyprint` package or the `pango` (and related) dev/runtime packages, then `pip install weasyprint`.

More: [WeasyPrint first steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) and [troubleshooting](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting).

---

## Office → PDF / PDF → Office (LibreOffice)

The **Office → PDF** and **PDF → Office** tools use **LibreOffice** in headless mode. If you see *"The system cannot find the file specified"* (WinError 2), LibreOffice is not installed or not on your PATH. If you see *"Could not find platform independent libraries"* or *"no export filter"*, the app now runs LibreOffice with its install directory as the working directory so it can find its components — ensure LibreOffice is installed in the default location or set `LIBREOFFICE_CMD` to the full path to `soffice.exe`.

### Windows

1. **Install LibreOffice**  
   Download and install from [libreoffice.org](https://www.libreoffice.org/download/download/). Default install path: `C:\Program Files\LibreOffice\program\soffice.exe`.

2. **No PATH needed**  
   This app will try to find `soffice.exe` in the default install folder. You only need to add it to PATH if you installed LibreOffice somewhere else.

3. **Custom install path**  
   Set the environment variable `LIBREOFFICE_CMD` to the full path of `soffice.exe` (e.g. `D:\LibreOffice\program\soffice.exe`).

### macOS / Linux

- **macOS:** `brew install libreoffice`  
- **Linux:** Install the `libreoffice` (or `libreoffice-core`) package from your distribution.

---

**PDF to image (for OCR)** uses **Poppler**. On Windows, if you get errors about `pdftoppm`/poppler, install it from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) and add the `bin` folder to your PATH.

---

## Deployment

- **Environment variables:** See `.env.example` for optional config (paths for Tesseract, LibreOffice, job storage). Copy to `.env` for local use only — **never commit `.env` or any file containing secrets to Git.**
- **Docker:** Use the included `Dockerfile` for containerized deployment (e.g. Oracle Cloud, any VPS).
