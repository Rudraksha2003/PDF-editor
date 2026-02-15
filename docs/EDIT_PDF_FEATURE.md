# PDF Text Editing Feature — Feasibility & Implementation Plan

## Executive summary

| Scenario | Possible? | Same font & size? | Notes |
|----------|------------|-------------------|--------|
| **Edit existing digital PDF** (selectable text) | **Yes** | **Yes** (with caveats) | Use PyMuPDF: extract spans with font/size/position → replace in place. |
| **Image → PDF → edit** | **Yes** | **Partially** | Editable: yes (OCR + overlay or reflow). Same *size*: approximate from bbox. Same *font*: **no** — OCR does not detect font. |

Few products do this well because: (1) PDF is a layout format, not a document model; (2) fonts are often embedded subsets; (3) image-sourced content has no font metadata. A solid, "full‑proof" implementation is possible for **digital PDFs**; for **image-sourced PDFs** we can deliver "edit with sensible font/size" but not "pixel‑perfect same font and size from the image."

---

## Part 1: Is it possible?

### 1.1 Edit any (digital) PDF with same font and size

**Yes, with the right stack.**

- **Extract**: Per-span text with position, font name, size, color (e.g. PyMuPDF `page.get_text("dict")`).
- **Replace**: Redact original span (e.g. white rect or remove), then insert new text at same position with same `fontsize` and, when possible, same `fontname`.
- **Limitations**:
  - **Font name**: PDF often stores internal names (e.g. `F1`, `Arial-BoldMT`). Mapping to a font PyMuPDF can use for `insert_text()` may require normalization (e.g. strip `-MT`, try built-ins like `helv`/`times`/`courier`, or use embedded font reference).
  - **Embedded subset fonts**: Only the glyphs used in the original PDF may be embedded. New characters in the replacement text might be missing → need fallback font or "replace with closest available" behavior.
  - **Layout**: Replacing with longer/shorter text can overflow or leave gap. Options: clip to bbox, scale down, or allow overflow (simplest for MVP).

So: **editing digital PDFs with same font and size is feasible and can be made solid** for most common cases (standard fonts, Latin script). Edge cases (subset fonts, rare scripts) need fallbacks and clear UX.

### 1.2 Image → PDF → edit with "same" font and size

**Edit: yes. Same font and size: only approximate.**

- **Image → PDF**: You already have this (img-to-pdf). The result is typically an image per page (no text layer).
- **Making it "editable"**: Run OCR (you have Tesseract), get text + bounding boxes. Then either:
  - Overlay a text layer (invisible or visible) so the PDF is searchable/selectable, or
  - Build a new PDF that draws the image as background and places text boxes on top using OCR text and box positions.
- **Same font**: **Not possible in general.** OCR does not detect font family. Tesseract outputs with a single internal font (e.g. GlyphLessFont). So we **cannot** guarantee "same font" from the image.
- **Same size**: **Approximate.** We can use the OCR bounding box height (and optionally width) to infer a point size so that inserted text fits the same region. So "same size" can be "same apparent size in the same place," not "exact original font metrics."

**Practical offer:**  
"Convert image to PDF and edit it: we'll place text in the right positions and use a **sensible size** (derived from bbox) and a **default or user-chosen font** (e.g. Helvetica, or a configurable fallback)." That is achievable and can be marketed as "edit any image-as-PDF with consistent, predictable formatting."

---

## Part 2: Why few products do this well

1. **PDF is layout, not structure** — Text is positioned glyphs, not a flow. Editing implies either in-place replacement (complex mapping) or full reflow (different product).
2. **Fonts** — Subset embedding, internal names, and missing glyphs make "same font" hard for arbitrary PDFs.
3. **Image-sourced content** — No font/size metadata; OCR gives text and position, not typography.
4. **Expectations** — Users expect Word-like editing; PDF was not designed for that, so products either limit scope or invest heavily in layout engines.

A realistic USP is: **"Edit text in PDFs and image-sourced PDFs with preserved or sensible formatting (position, size, and font where available)."**

---

## Part 3: What is required

### 3.1 Dependencies

| Dependency | Purpose |
|------------|--------|
| **PyMuPDF** (`pymupdf`) | Extract text with font/size/bbox; redact; insert text with font/size; optional OCR integration. |
| **Existing** | `pdfplumber` / `pypdf` for other jobs; `pytesseract` + `pdf2image` for OCR; `reportlab` for some drawing. |

You currently use **pypdf**, **pdfplumber**, **reportlab** — not PyMuPDF. For robust in-place text editing with font/size, **PyMuPDF is the right choice**; it can coexist with the rest.

### 3.2 Capabilities to implement

1. **Structured text extraction (for editing)**  
   Return, per page, a list of "text spans" with: `text`, `bbox`, `font_name`, `font_size`, `color`, `page_index`.  
   This powers: (a) UI that shows "what can be edited," (b) backend that knows where and how to replace.

2. **In-place text replacement (digital PDF)**  
   - Input: PDF + one or more "replacements" (e.g. `old_text` or `span_id` + `new_text`).  
   - Logic: Locate span (by text search or bbox), redact (e.g. white rect), insert new text with same `fontsize` and best-effort same `fontname` (with fallback).  
   - Output: New PDF.

3. **Font handling**  
   - Map PDF font names to PyMuPDF `insert_text()` font names (e.g. `helv`, `times`, `courier`, or embedded).  
   - If replacement text needs a glyph not in the original font, use a fallback (e.g. built-in or embedded) and document this in API/UI.

4. **Image → PDF → edit pipeline**  
   - Input: Image(s) or image-based PDF.  
   - Steps: (1) Image → PDF if needed (existing), (2) OCR (existing) to get text + bboxes, (3) For each text region: insert text at bbox with **size from bbox height** and **default or user-specified font**.  
   - Result: Editable PDF with "sensible" font and size, not "same as image" (which is unknown).

### 3.3 API shape (high level)

- `GET /edit-pdf/content?job_id=...` or `POST /edit-pdf/extract`  
  → Returns structured list of text spans (text, bbox, font_name, font_size, color, page).

- `POST /edit-pdf/replace`  
  → Body: `job_id`, `replacements: [{ "old_text" | "span_id", "new_text" }, ...]`.  
  → Returns new job_id or download for edited PDF.

- Optional: `POST /edit-pdf/from-image`  
  → Image(s) → PDF → OCR → return same span structure + editable PDF (sizes from bbox, default font).  
  Then same `POST /edit-pdf/replace` can apply.

---

## Part 4: Phased implementation plan

### Phase 1: Edit digital PDFs (core USP)

**Goal:** User uploads a digital PDF; gets back span list; sends replacements; gets PDF with text changed, same font and size where possible.

1. **Add PyMuPDF** to `requirements.txt` and use it only in the new edit workflow (no need to refactor existing jobs immediately).
2. **Implement span extraction**  
   - Open PDF with PyMuPDF; for each page, `get_text("dict")`; normalize to a simple list of spans (text, bbox, font, size, color, page).  
   - Expose via endpoint (e.g. `POST /edit-pdf/extract` with file upload) and return JSON.
3. **Implement replace**  
   - For each replacement: `page.search_for(old_text)` or match by bbox; get span props; draw white rect over old text; `page.insert_text(point, new_text, fontsize=..., fontname=...)` with font name mapping and fallback.  
   - Handle multiple occurrences (e.g. replace first, or all, or by span_id).
4. **Font mapping**  
   - Build a small map: PDF font name → PyMuPDF font name (e.g. `Arial` → `helv`, `Times` → `times`).  
   - For unknown/embedded: try `page.get_fonts()` and use ref if possible; else fallback to `helv` and log.
5. **Edge cases**  
   - Longer replacement: either clip to bbox, or allow overflow (MVP).  
   - Subset font missing glyph: fallback font + optional API flag "strict_font: false".
6. **Tests**  
   - Sample PDFs: standard fonts, embedded font, multi-page, non-Latin if needed.  
   - Assert: output PDF contains new text at expected position and approximate font size.

### Phase 2: Image → PDF → edit (same pipeline, best-effort font/size)

**Goal:** User uploads image(s); we produce an "editable" PDF (or image→PDF then OCR); span list uses sizes from OCR bbox and a default font; same replace API applies.

1. **Reuse OCR** (existing): Image or image-PDF → pages as images → Tesseract → text + bboxes per word/line.
2. **Build editable PDF**  
   - One page per image; draw image as background; for each OCR span, `insert_text(bbox_tl, text, fontsize=from_bbox_height, fontname=default_font)`.  
   - Optionally store span list (with bbox, inferred size, font=default) for that PDF.
3. **Expose as "edit from image"**  
   - Single flow: upload image → return PDF + span list (sizes from bbox, font = default).  
   - Document: "Font and size are chosen for consistency; original image font is not detected."
4. **Optional**  
   - Let user pass `font_name` / `font_size` for "image-sourced" edits (override default).

### Phase 3: Robustness and UX

- **Strict vs. best-effort**: API flag to fail if font cannot be preserved vs. always fallback.
- **Quads for rotated text**: Use PyMuPDF quads when `line["dir"] != (1,0)` for accurate redact/insert.
- **Unicode and scripts**: Test with your target languages; use PyMuPDF's font fallback or `insert_htmlbox` if needed for complex scripts.
- **Rate limits and size limits**: Reuse your existing validation (e.g. max file size, max pages) for edit endpoints.

---

## Part 5: Summary

| Question | Answer |
|----------|--------|
| Can we implement "edit PDF" as a USP? | **Yes.** |
| Same font and size for any PDF? | **Digital PDF: yes, with fallbacks for subset/unknown fonts. Image PDF: size ≈ from bbox, font = default or user choice.** |
| Same font and size from an image? | **Size: approximate. Font: no — OCR doesn't provide it; we use a sensible default.** |
| What's required? | **PyMuPDF, structured extraction API, replace API, font mapping + fallback, optional image→PDF→edit pipeline.** |
| Why do few products do it? | **PDF is layout-based; fonts are messy; image has no typography. A solid implementation is still possible with clear scope.** |

Recommended positioning: **"Edit text in any PDF and in image-sourced PDFs with preserved or consistent formatting (same font and size when the PDF provides it; sensible font and size for images)."** That is achievable, defensible, and can be made solid with the phased plan above.

If you want to proceed, the next concrete step is **Phase 1**: add PyMuPDF, implement extract + replace for digital PDFs, and add tests and one API route (e.g. `POST /edit-pdf/replace`) plus an optional `POST /edit-pdf/extract`.
