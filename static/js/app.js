/**
 * PDF Editor — Frontend app
 * Talks to FastAPI backend: upload → job → poll → download
 * File cards with thumbnails (PDF.js for PDFs, object URL for images).
 */

// PDF.js worker (must be set before any getDocument calls)
if (typeof pdfjsLib !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}

const API = {
  base: '',
  async postFormData(url, formData) {
    const res = await fetch(`${this.base}${url}`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || err.message || 'Request failed');
    }
    return res.json();
  },
  async postJSON(url, body) {
    const res = await fetch(`${this.base}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || err.message || 'Request failed');
    }
    return res.json();
  },
  async get(url) {
    const res = await fetch(`${this.base}${url}`);
    if (!res.ok) throw new Error(res.statusText);
    return res.json();
  },
};

const TOOLS = {
  merge: {
    title: 'Merge PDFs',
    multi: true,
    minFiles: 2,
    orderMatters: true,
    accept: '.pdf,application/pdf',
    dropText: 'Drop PDFs here or click to browse',
    dropHint: 'At least 2 PDFs — order = merge order',
    submit: async (files) => {
      const fd = new FormData();
      files.forEach((f) => fd.append('files', f));
      return API.postFormData('/merge', fd);
    },
  },
  split: {
    title: 'Split PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'One PDF per page, delivered as ZIP',
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/split', fd);
    },
  },
  compress: {
    title: 'Compress PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Reduces file size',
    options: [
      { id: 'method', label: 'Compression method', type: 'radio', name: 'method', choices: [{ value: 'quality', label: 'Quality' }, { value: 'file_size', label: 'File Size' }], default: 'quality' },
      { id: 'compression_level', label: 'Compression level (1–9)', type: 'slider', name: 'compression_level', min: 1, max: 9, default: 5, compressMode: 'quality' },
      { id: 'desired_size', label: 'Desired file size', type: 'number', name: 'desired_size', placeholder: 'Enter size', default: '', compressMode: 'file_size' },
      { id: 'desired_size_unit', label: 'Unit', type: 'select', name: 'desired_size_unit', choices: ['KB', 'MB'], compressMode: 'file_size' },
      { id: 'grayscale', label: 'Apply grayscale for compression', type: 'checkbox', name: 'grayscale', default: false },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('method', params.method || 'quality');
      fd.append('compression_level', parseInt(params.compression_level, 10) || 5);
      fd.append('desired_size', parseFloat(params.desired_size) || 0);
      fd.append('desired_size_unit', params.desired_size_unit || 'MB');
      fd.append('grayscale', params.grayscale === true || params.grayscale === 'true' ? 'true' : 'false');
      return API.postFormData('/compress', fd);
    },
  },
  extract: {
    title: 'Extract pages',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'e.g. 1,3,5-7',
    options: [
      { id: 'pages', label: 'Pages (e.g. 1,3,5-7)', type: 'text', name: 'pages', placeholder: '1, 2, 5-10' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('pages', params.pages.trim());
      return API.postFormData('/extract', fd);
    },
  },
  rotate: {
    title: 'Rotate pages',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Choose pages and angle',
    options: [
      { id: 'pages', label: 'Pages (e.g. 1,3,5)', type: 'text', name: 'pages', placeholder: '1, 2, 3' },
      { id: 'angle', label: 'Angle', type: 'select', name: 'angle', choices: [90, 180, 270] },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('pages', params.pages.trim());
      fd.append('angle', parseInt(params.angle, 10));
      return API.postFormData('/rotate', fd);
    },
  },
  'img-to-pdf': {
    title: 'Images → PDF',
    multi: true,
    orderMatters: true,
    accept: 'image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif',
    dropText: 'Drop images here or click to browse',
    dropHint: 'Order = page order in PDF',
    submit: async (files) => {
      const fd = new FormData();
      files.forEach((f) => fd.append('files', f));
      return API.postFormData('/img-to-pdf', fd);
    },
  },
  'pdf-to-img': {
    title: 'PDF → Images',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Export as JPG or PNG (ZIP)',
    options: [
      { id: 'format', label: 'Format', type: 'select', name: 'format', choices: ['jpg', 'png'] },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('format', params.format);
      return API.postFormData('/pdf-to-img', fd);
    },
  },
  'split-by-range': {
    title: 'Split by range',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'e.g. 1-3,4-6,7 → 3 PDFs in a ZIP',
    options: [
      { id: 'ranges', label: 'Page ranges (e.g. 1-3,4-6,7)', type: 'text', name: 'ranges', placeholder: '1-3, 4-5, 7' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('ranges', params.ranges.trim());
      return API.postFormData('/split-by-range', fd);
    },
  },
  delete: {
    title: 'Delete pages',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Comma-separated page numbers to remove',
    options: [
      { id: 'pages', label: 'Pages to delete (e.g. 2,4,6)', type: 'text', name: 'pages', placeholder: '2, 4, 6' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('pages', params.pages.trim());
      return API.postFormData('/delete', fd);
    },
  },
  reorder: {
    title: 'Reorder pages',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'New order: e.g. 3,1,2',
    options: [
      { id: 'order', label: 'Page order (e.g. 3,1,2)', type: 'text', name: 'order', placeholder: '3, 1, 2' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('order', params.order.trim());
      return API.postFormData('/reorder', fd);
    },
  },
  compare: {
    title: 'Compare PDFs',
    multi: true,
    minFiles: 2,
    maxFiles: 2,
    accept: '.pdf,application/pdf',
    dropText: 'Drop 2 PDFs here or click to browse',
    dropHint: 'Exactly 2 PDFs — get a diff report',
    submit: async (files) => {
      const fd = new FormData();
      fd.append('files', files[0]);
      fd.append('files', files[1]);
      return API.postFormData('/compare', fd);
    },
  },
  repair: {
    title: 'Repair PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Try to fix corrupted PDFs',
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/repair', fd);
    },
  },
  ocr: {
    title: 'OCR PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Extract text from scanned pages',
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/ocr', fd);
    },
  },
  'pdf-to-pdfa': {
    title: 'PDF → PDF/A',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Archive-ready PDF/A',
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/pdf-to-pdfa', fd);
    },
  },
  'pdf-to-text': {
    title: 'PDF → Text',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Export as .txt or .md',
    options: [
      { id: 'format', label: 'Format', type: 'select', name: 'format', choices: ['text', 'markdown'] },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('format', params.format);
      return API.postFormData('/pdf-to-text', fd);
    },
  },
  'html-to-pdf': {
    title: 'HTML → PDF',
    multi: false,
    accept: '.html,.htm,text/html',
    dropText: 'Drop an HTML file here or click to browse',
    dropHint: 'Or enter a website URL below to convert the page to PDF',
    allowUrlAsAlternative: true,
    options: [
      { id: 'url', label: 'Or website URL', type: 'text', name: 'url', placeholder: 'https://example.com', note: 'Not recommended — conversion is slow and layout is often distorted. Upload an HTML file for better results.' },
    ],
    submit: async (files, params) => {
      const url = (params?.url || '').trim();
      if (url) {
        return API.postJSON('/html-to-pdf-from-url', { url });
      }
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/html-to-pdf', fd);
    },
  },
  'office-to-pdf': {
    title: 'Office → PDF',
    multi: false,
    accept: '.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.presentationml.presentation',
    dropText: 'Drop a Word/Excel/PPT file here or click to browse',
    dropHint: 'Doc, DOCX, XLS, XLSX, PPT, PPTX, ODT, ODS, ODP',
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/office-to-pdf', fd);
    },
  },
  'pdf-to-office': {
    title: 'PDF → Office',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Export as DOCX, XLSX, or PPTX',
    options: [
      { id: 'format', label: 'Format', type: 'select', name: 'format', choices: ['docx', 'xlsx', 'pptx'] },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('format', params.format);
      return API.postFormData('/pdf-to-office', fd);
    },
  },
  crop: {
    title: 'Crop (margins)',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Margin in points (left, bottom, right, top)',
    options: [
      { id: 'left', label: 'Left (pt)', type: 'number', name: 'left', default: 0 },
      { id: 'bottom', label: 'Bottom (pt)', type: 'number', name: 'bottom', default: 0 },
      { id: 'right', label: 'Right (pt)', type: 'number', name: 'right', default: 0 },
      { id: 'top', label: 'Top (pt)', type: 'number', name: 'top', default: 0 },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('left', parseFloat(params.left) || 0);
      fd.append('bottom', parseFloat(params.bottom) || 0);
      fd.append('right', parseFloat(params.right) || 0);
      fd.append('top', parseFloat(params.top) || 0);
      return API.postFormData('/crop', fd);
    },
  },
  'page-numbers': {
    title: 'Add page numbers',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'e.g. Page 1 of N',
    options: [
      { id: 'template', label: 'Template ({n}=page, {total}=total)', type: 'text', name: 'template', placeholder: 'Page {n} of {total}' },
      { id: 'position', label: 'Position', type: 'select', name: 'position', choices: ['bottom_center', 'bottom_right', 'top_center', 'top_right', 'bottom_left', 'top_left'] },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('template', params.template.trim() || 'Page {n} of {total}');
      fd.append('position', params.position);
      return API.postFormData('/page-numbers', fd);
    },
  },
  watermark: {
    title: 'Add watermark',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Text watermark on every page',
    options: [
      { id: 'text', label: 'Watermark text', type: 'text', name: 'text', placeholder: 'DRAFT' },
      { id: 'opacity', label: 'Opacity (0.1–1)', type: 'number', name: 'opacity', default: 0.5 },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('text', params.text.trim() || 'Watermark');
      fd.append('opacity', parseFloat(params.opacity) || 0.5);
      return API.postFormData('/watermark', fd);
    },
  },
  stamp: {
    title: 'Add stamp (image)',
    multi: true,
    minFiles: 2,
    maxFiles: 2,
    accept: '.pdf,application/pdf,image/png,image/jpeg,image/jpg',
    dropText: 'Drop PDF then stamp image (PNG/JPG)',
    dropHint: 'First: PDF, second: image',
    options: [
      { id: 'position', label: 'Position', type: 'select', name: 'position', choices: ['bottom_right', 'bottom_left', 'top_right', 'top_left', 'center'] },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('stamp', files[1]);
      fd.append('position', params.position || 'bottom_right');
      return API.postFormData('/stamp', fd);
    },
  },
  flatten: {
    title: 'Flatten PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Forms/annotations → static content',
    optionsTitle: 'Flatten options',
    options: [
      { id: 'flatten_only_forms', label: 'Flatten only forms', type: 'checkbox', name: 'flatten_only_forms', default: false, note: 'Only flatten form fields, leaving links and other annotations intact.' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('flatten_only_forms', params.flatten_only_forms === true || params.flatten_only_forms === 'true' ? 'true' : 'false');
      return API.postFormData('/flatten', fd);
    },
  },
  'remove-blanks': {
    title: 'Remove blank pages',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Detects and removes blank pages',
    options: [
      { id: 'threshold', label: 'Blank threshold (0–1)', type: 'number', name: 'threshold', default: 0.01 },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('threshold', parseFloat(params.threshold) || 0.01);
      return API.postFormData('/remove-blanks', fd);
    },
  },
  'extract-images': {
    title: 'Extract images',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'All images as ZIP',
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/extract-images', fd);
    },
  },
  protect: {
    title: 'Protect (password)',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Set a password to lock',
    options: [
      { id: 'password', label: 'Password', type: 'password', name: 'password', placeholder: 'Enter password' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('password', params.password);
      return API.postFormData('/protect', fd);
    },
  },
  unlock: {
    title: 'Unlock PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Remove password with current password',
    options: [
      { id: 'password', label: 'Current password', type: 'password', name: 'password', placeholder: 'Enter password' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('password', params.password);
      return API.postFormData('/unlock', fd);
    },
  },
  redact: {
    title: 'Redact text',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Comma-separated phrases to redact',
    options: [
      { id: 'search', label: 'Phrases to redact (comma-separated)', type: 'text', name: 'search', placeholder: 'secret, confidential' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('search', params.search.trim());
      return API.postFormData('/redact', fd);
    },
  },
  sign: {
    title: 'Sign PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop PDF to sign',
    dropHint: 'Then add certificate and optional key below',
    extraFiles: [
      { name: 'cert', label: 'Certificate (.pem or .crt)', accept: '.pem,.crt', required: true },
      { name: 'key', label: 'Private key (.pem) — optional', accept: '.pem', required: false },
    ],
    options: [],
    submit: async (files, params, extraFiles) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('cert', extraFiles.cert);
      if (extraFiles.key) fd.append('key', extraFiles.key);
      return API.postFormData('/sign', fd);
    },
  },
  sanitize: {
    title: 'Sanitize PDF',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Select the elements you want to remove from the PDF',
    optionsTitle: 'Sanitisation options',
    optionsHint: 'Select the elements you want to remove from the PDF. At least one option must be selected.',
    options: [
      { id: 'remove_javascript', label: 'Remove JavaScript', type: 'checkbox', name: 'remove_javascript', default: true, note: 'Remove JavaScript actions and scripts from the PDF.' },
      { id: 'remove_embedded_files', label: 'Remove embedded files', type: 'checkbox', name: 'remove_embedded_files', default: true, note: 'Remove any files embedded within the PDF.' },
      { id: 'remove_xmp_metadata', label: 'Remove XMP metadata', type: 'checkbox', name: 'remove_xmp_metadata', default: false, note: 'Remove XMP metadata from the PDF.' },
      { id: 'remove_document_metadata', label: 'Remove document metadata', type: 'checkbox', name: 'remove_document_metadata', default: false, note: 'Remove document information metadata (title, author, etc.).' },
      { id: 'remove_links', label: 'Remove links', type: 'checkbox', name: 'remove_links', default: false, note: 'Remove external links and launch actions from the PDF.' },
      { id: 'remove_fonts', label: 'Remove fonts', type: 'checkbox', name: 'remove_fonts', default: false, note: 'Remove embedded fonts from the PDF.' },
    ],
    submit: async (files, params) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      fd.append('remove_javascript', (params.remove_javascript === true || params.remove_javascript === 'true') ? 'true' : 'false');
      fd.append('remove_embedded_files', (params.remove_embedded_files === true || params.remove_embedded_files === 'true') ? 'true' : 'false');
      fd.append('remove_xmp_metadata', (params.remove_xmp_metadata === true || params.remove_xmp_metadata === 'true') ? 'true' : 'false');
      fd.append('remove_document_metadata', (params.remove_document_metadata === true || params.remove_document_metadata === 'true') ? 'true' : 'false');
      fd.append('remove_links', (params.remove_links === true || params.remove_links === 'true') ? 'true' : 'false');
      fd.append('remove_fonts', (params.remove_fonts === true || params.remove_fonts === 'true') ? 'true' : 'false');
      return API.postFormData('/sanitize', fd);
    },
  },
  'document-info': {
    title: 'Document info',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'Page count and metadata (no download)',
    syncResponse: true,
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/document-info', fd);
    },
  },
  'form-fields': {
    title: 'Form fields',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a PDF here or click to browse',
    dropHint: 'List form fields (no download)',
    syncResponse: true,
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/form-fields', fd);
    },
  },
  'validate-signature': {
    title: 'Validate signature',
    multi: false,
    accept: '.pdf,application/pdf',
    dropText: 'Drop a signed PDF here or click to browse',
    dropHint: 'Check signature info (no download)',
    syncResponse: true,
    submit: async (files) => {
      const fd = new FormData();
      fd.append('file', files[0]);
      return API.postFormData('/validate-signature', fd);
    },
  },
};

// ----- DOM -----
const homeView = document.getElementById('homeView');
const workspace = document.getElementById('workspace');
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const workspaceTitle = document.getElementById('workspaceTitle');
const backBtn = document.getElementById('backBtn');
const toolSearch = document.getElementById('toolSearch');
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const dropText = document.getElementById('dropText');
const dropHint = document.getElementById('dropHint');
const toolOptions = document.getElementById('toolOptions');
const submitBtn = document.getElementById('submitBtn');
const jobPanel = document.getElementById('jobPanel');
const jobStatus = document.getElementById('jobStatus');
const downloadBtn = document.getElementById('downloadBtn');
const previewView = document.getElementById('previewView');
const previewViewEmpty = document.getElementById('previewViewEmpty');
const previewViewIframe = document.getElementById('previewViewIframe');
const toastContainer = document.getElementById('toastContainer');
const fileCards = document.getElementById('fileCards');
const fileVizInstruction = document.getElementById('fileVizInstruction');
const fileVizActions = document.getElementById('fileVizActions');
const addMoreBtn = document.getElementById('addMoreBtn');
const sortBtnAZ = document.getElementById('sortBtnAZ');
const sortBtnZA = document.getElementById('sortBtnZA');
const addMoreBadge = document.getElementById('addMoreBadge');
const fileCardsWrap = document.querySelector('.file-cards-wrap');
const uploadNewFileBtn = document.getElementById('uploadNewFileBtn');
const openCompareViewBtn = document.getElementById('openCompareViewBtn');
const themeToggle = document.getElementById('themeToggle');
const appRoot = document.getElementById('appRoot');
const compareView = document.getElementById('compareView');
const compareViewBackBtn = document.getElementById('compareViewBackBtn');
const compareCanvasWrapLeft = document.getElementById('compareCanvasWrapLeft');
const compareCanvasWrapRight = document.getElementById('compareCanvasWrapRight');
const compareLabelLeft = document.getElementById('compareLabelLeft');
const compareLabelRight = document.getElementById('compareLabelRight');
const compareReportCount = document.getElementById('compareReportCount');
const compareReportList = document.getElementById('compareReportList');
const compareReportSearch = document.getElementById('compareReportSearch');
const compareDownloadReportBtn = document.getElementById('compareDownloadReportBtn');
const compareScrollSync = document.getElementById('compareScrollSync');
const compareZoomIn = document.getElementById('compareZoomIn');
const compareZoomOut = document.getElementById('compareZoomOut');
const compareZoomLabel = document.getElementById('compareZoomLabel');

const THEME_STORAGE_KEY = 'pdf-editor-theme';
const VIEW_STORAGE_KEY = 'pdf-editor-view';

function getStoredTheme() {
  try {
    const t = localStorage.getItem(THEME_STORAGE_KEY);
    if (t === 'light' || t === 'dark') return t;
  } catch (_) {}
  return 'dark';
}

function setTheme(theme) {
  const root = document.documentElement;
  root.setAttribute('data-theme', theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch (_) {}
  if (themeToggle) {
    const label = theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode';
    themeToggle.setAttribute('title', label);
    themeToggle.setAttribute('aria-label', label);
  }
}

function initTheme() {
  setTheme(getStoredTheme());
}

function getStoredView() {
  try {
    const v = localStorage.getItem(VIEW_STORAGE_KEY);
    if (v === 'tools' || v === 'reader') return v;
  } catch (_) {}
  return 'tools';
}

function setView(view) {
  if (view !== 'tools' && view !== 'reader' && view !== 'preview' && view !== 'compare') view = 'tools';
  if (appRoot) appRoot.setAttribute('data-view', view);
  document.querySelectorAll('.view-tab').forEach((tab) => {
    const isActive = tab.dataset.view === view;
    tab.classList.toggle('active', isActive);
    tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });
  if (view === 'compare') {
    compareView?.classList.remove('hidden');
    compareView?.setAttribute('aria-hidden', 'false');
    homeView?.classList.add('hidden');
    workspace?.classList.add('hidden');
    workspace?.setAttribute('aria-hidden', 'true');
    previewView?.classList.add('hidden');
    previewView?.setAttribute('aria-hidden', 'true');
  } else {
    compareView?.classList.add('hidden');
    compareView?.setAttribute('aria-hidden', 'true');
  }
  if (view === 'preview') {
    previewView?.classList.remove('hidden');
    previewView?.setAttribute('aria-hidden', 'false');
    homeView?.classList.add('hidden');
    workspace?.classList.add('hidden');
    workspace?.setAttribute('aria-hidden', 'true');
    if (lastPreviewJobId && previewViewIframe && previewViewEmpty) {
      previewViewIframe.src = `${API.base}/preview/${lastPreviewJobId}#view=Fit`;
      previewViewIframe.classList.remove('hidden');
      previewViewEmpty.classList.add('hidden');
    } else {
      previewViewIframe?.classList.add('hidden');
      if (previewViewIframe) previewViewIframe.src = '';
      previewViewEmpty?.classList.remove('hidden');
    }
  } else if (view !== 'compare') {
    previewView?.classList.add('hidden');
    previewView?.setAttribute('aria-hidden', 'true');
    if (previewViewIframe) previewViewIframe.src = '';
    if (view === 'tools' || view === 'reader') {
      homeView?.classList.toggle('hidden', !!currentTool);
      workspace?.classList.toggle('hidden', !currentTool);
      workspace?.setAttribute('aria-hidden', currentTool ? 'false' : 'true');
    }
  }
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, view);
  } catch (_) {}
}

function initView() {
  setView(getStoredView());
}

let currentTool = null;
let currentToolKey = null;
let selectedFiles = [];
let addMoreMode = false;
let lastPreviewJobId = null;
let lastCompareJobId = null;

// ----- Toasts -----
function toast(message, isError = false) {
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' error' : '');
  el.textContent = message;
  toastContainer.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ----- Tool selection -----
function showWorkspace(toolKey) {
  currentTool = TOOLS[toolKey];
  currentToolKey = toolKey;
  if (!currentTool) return;

  homeView?.classList.add('hidden');
  workspace.classList.remove('hidden');
  workspace.setAttribute('aria-hidden', 'false');
  workspaceTitle.textContent = currentTool.title;
  document.querySelectorAll('.nav-tool').forEach((el) => {
    el.classList.toggle('active', el.dataset.tool === toolKey);
  });

  dropText.textContent = currentTool.dropText;
  dropHint.textContent = currentTool.dropHint || '';
  fileInput.accept = currentTool.accept;
  fileInput.multiple = currentTool.multi;

  selectedFiles = [];
  addMoreMode = false;
  lastPreviewJobId = null;
  document.querySelector('.view-tab[data-view="preview"]')?.classList.remove('has-preview');
  if (previewViewIframe) previewViewIframe.src = '';
  if (previewViewEmpty) previewViewEmpty.classList.remove('hidden');
  if (previewViewIframe) previewViewIframe.classList.add('hidden');
  dropZone.classList.remove('has-files', 'drag-over');
  fileCardsWrap?.classList.remove('has-files', 'drag-over');
  updateFileVizVisibility();
  renderFileCards();
  renderOptions();
  const flattenOptionsBlock = document.getElementById('flattenOptionsBlock');
  if (flattenOptionsBlock) {
    flattenOptionsBlock.classList.toggle('hidden', toolKey !== 'flatten');
    if (toolKey === 'flatten') {
      const cb = document.getElementById('opt-flatten_only_forms');
      if (cb) cb.checked = false;
    }
  }
  hideJobPanel();
  updateSubmitButton();
  if (sidebar?.classList.contains('sidebar-open')) {
    sidebar.classList.remove('sidebar-open');
    sidebarToggle?.setAttribute('aria-expanded', 'false');
    sidebarToggle?.setAttribute('aria-label', 'Open tools menu');
  }
}

function showHome() {
  currentTool = null;
  currentToolKey = null;
  selectedFiles = [];
  lastPreviewJobId = null;
  document.querySelector('.view-tab[data-view="preview"]')?.classList.remove('has-preview');
  if (previewViewIframe) previewViewIframe.src = '';
  if (previewViewEmpty) previewViewEmpty.classList.remove('hidden');
  if (previewViewIframe) previewViewIframe.classList.add('hidden');
  workspace.classList.add('hidden');
  workspace.setAttribute('aria-hidden', 'true');
  homeView?.classList.remove('hidden');
  document.querySelectorAll('.nav-tool').forEach((el) => el.classList.remove('active'));
  hideJobPanel();
}

function renderOptions() {
  if (currentToolKey === 'flatten') {
    toolOptions.classList.add('hidden');
    toolOptions.innerHTML = '';
    return;
  }
  const opts = currentTool?.options || [];
  const extraFiles = currentTool?.extraFiles || [];
  const hasOpts = opts.length > 0 || extraFiles.length > 0;
  if (!hasOpts) {
    toolOptions.classList.add('hidden');
    toolOptions.innerHTML = '';
    return;
  }
  toolOptions.classList.remove('hidden');
  let html = '';
  if (currentTool?.optionsTitle) {
    html += `<div class="options-section-title"><span class="options-section-title-text">${currentTool.optionsTitle}</span></div>`;
  }
  html += opts.map((o) => {
    if (o.type === 'select') {
      const options = o.choices.map((c) => `<option value="${c}">${c}</option>`).join('');
      const dataMode = o.compressMode ? ` data-compress-mode="${o.compressMode}"` : '';
      return `<div class="option-group"${dataMode}><label for="opt-${o.id}">${o.label}</label><select id="opt-${o.id}" name="${o.name}">${options}</select></div>`;
    }
    if (o.type === 'number') {
      const val = o.default !== undefined ? o.default : '';
      const dataMode = o.compressMode ? ` data-compress-mode="${o.compressMode}"` : '';
      return `<div class="option-group"${dataMode}><label for="opt-${o.id}">${o.label}</label><input type="number" id="opt-${o.id}" name="${o.name}" value="${val}" step="any" placeholder="${o.placeholder || ''}" /></div>`;
    }
    if (o.type === 'password') {
      return `<div class="option-group"><label for="opt-${o.id}">${o.label}</label><input type="password" id="opt-${o.id}" name="${o.name}" placeholder="${o.placeholder || ''}" /></div>`;
    }
    if (o.type === 'radio') {
      const defaultVal = o.default !== undefined ? o.default : (o.choices && o.choices[0]?.value);
      const radios = (o.choices || []).map((c) => {
        const val = typeof c === 'object' ? c.value : c;
        const lbl = typeof c === 'object' ? c.label : c;
        const checked = val === defaultVal ? ' checked' : '';
        return `<label class="option-radio-label"><input type="radio" id="opt-${o.id}-${val}" name="${o.name}" value="${val}"${checked} /><span>${lbl}</span></label>`;
      }).join('');
      return `<div class="option-group option-group-radio"><span class="option-label">${o.label}</span><div class="option-radios">${radios}</div></div>`;
    }
    if (o.type === 'slider') {
      const min = o.min !== undefined ? o.min : 0;
      const max = o.max !== undefined ? o.max : 100;
      const val = o.default !== undefined ? o.default : Math.round((min + max) / 2);
      const dataMode = o.compressMode ? ` data-compress-mode="${o.compressMode}"` : '';
      return `<div class="option-group"${dataMode}><label for="opt-${o.id}">${o.label}</label><div class="option-slider-wrap"><input type="range" id="opt-${o.id}" name="${o.name}" min="${min}" max="${max}" value="${val}" class="option-slider" /><span class="option-slider-value" id="opt-${o.id}-value">${val}</span></div></div>`;
    }
    if (o.type === 'checkbox') {
      const checked = o.default ? ' checked' : '';
      const noteHtml = o.note ? `<p class="option-note">${o.note}</p>` : '';
      return `<div class="option-group option-group-checkbox"><label class="option-checkbox-label"><input type="checkbox" id="opt-${o.id}" name="${o.name}" value="true"${checked} /><span>${o.label}</span></label>${noteHtml}</div>`;
    }
    const noteHtml = o.note ? `<p class="option-note">${o.note}</p>` : '';
    return `<div class="option-group"><label for="opt-${o.id}">${o.label}</label>${noteHtml}<input type="text" id="opt-${o.id}" name="${o.name}" placeholder="${o.placeholder || ''}" /></div>`;
  }).join('');
  if (currentTool?.optionsHint) {
    html += `<p class="option-note options-hint">${currentTool.optionsHint}</p>`;
  }
  extraFiles.forEach((ef) => {
    html += `<div class="option-group"><label for="extra-${ef.name}">${ef.label}</label><input type="file" id="extra-${ef.name}" name="${ef.name}" accept="${ef.accept || ''}" class="extra-file-input" /></div>`;
  });
  toolOptions.innerHTML = html;
  opts.forEach((o) => {
    if (o.type === 'slider') {
      const el = document.getElementById(`opt-${o.id}`);
      const valueEl = document.getElementById(`opt-${o.id}-value`);
      if (el && valueEl) {
        const update = () => { valueEl.textContent = el.value; updateSubmitButton(); };
        el.addEventListener('input', update);
        update();
      }
    }
  });
  if (currentTool?.title === 'Compress PDF') {
    const updateCompressVisibility = () => {
      const method = (document.querySelector('input[name="method"]:checked') || {}).value || 'quality';
      toolOptions.querySelectorAll('[data-compress-mode]').forEach((div) => {
        div.style.display = div.dataset.compressMode === method ? '' : 'none';
      });
    };
    toolOptions.querySelectorAll('input[name="method"]').forEach((el) => el.addEventListener('change', updateCompressVisibility));
    updateCompressVisibility();
  }
  extraFiles.forEach((ef) => {
    const el = document.getElementById(`extra-${ef.name}`);
    if (el) el.addEventListener('change', updateSubmitButton);
  });
  toolOptions.querySelectorAll('input[type="checkbox"]').forEach((el) => el.addEventListener('change', updateSubmitButton));
  if (currentTool?.allowUrlAsAlternative) {
    const urlEl = document.getElementById('opt-url');
    if (urlEl) urlEl.addEventListener('input', updateSubmitButton);
  }
}

function getOptionParams() {
  const params = {};
  currentTool?.options?.forEach((o) => {
    if (o.type === 'radio') {
      const el = document.querySelector(`input[name="${o.name}"]:checked`);
      if (el) params[o.name] = el.value;
    } else if (o.type === 'checkbox') {
      const el = document.querySelector(`#opt-${o.id}`);
      if (el) params[o.name] = el.checked;
    } else {
      const el = document.querySelector(`#opt-${o.id}`);
      if (el) params[o.name] = el.value;
    }
  });
  return params;
}
function getOptionFiles() {
  const out = {};
  currentTool?.extraFiles?.forEach((ef) => {
    const el = document.querySelector(`#extra-${ef.name}`);
    if (el?.files?.length) out[ef.name] = el.files[0];
  });
  return out;
}

// ----- Files -----
function setFiles(files) {
  let list = Array.from(files || []);
  const maxFiles = currentTool?.maxFiles;
  if (maxFiles != null && list.length > maxFiles) list = list.slice(0, maxFiles);
  if (currentTool?.multi) {
    selectedFiles = list;
  } else {
    selectedFiles = list.length ? [list[0]] : [];
  }
  fileInput.value = '';
  dropZone.classList.toggle('has-files', selectedFiles.length > 0);
  fileCardsWrap?.classList.toggle('has-files', selectedFiles.length > 0);
  if (selectedFiles.length > 0) {
    dropText.textContent = selectedFiles.length === 1 ? selectedFiles[0].name : `${selectedFiles.length} files selected`;
  } else {
    dropText.textContent = currentTool?.dropText || 'Drop files here';
  }
  updateSubmitButton();
  updateFileVizVisibility();
  renderFileCards();
}

function clearFiles() {
  selectedFiles = [];
  addMoreMode = false;
  fileInput.value = '';
  lastPreviewJobId = null;
  document.querySelector('.view-tab[data-view="preview"]')?.classList.remove('has-preview');
  dropZone.classList.remove('has-files', 'drag-over');
  fileCardsWrap?.classList.remove('has-files', 'drag-over');
  dropText.textContent = currentTool?.dropText || 'Drop files here';
  hideJobPanel();
  updateSubmitButton();
  updateFileVizVisibility();
  renderFileCards();
}

function appendFiles(files) {
  const list = Array.from(files || []);
  if (!currentTool?.multi || list.length === 0) return;
  const maxFiles = currentTool?.maxFiles;
  if (maxFiles != null && selectedFiles.length >= maxFiles) return;
  const accept = (currentTool.accept || '').toLowerCase();
  const isPdfAccept = accept.includes('pdf');
  const isImageAccept = accept.includes('image');
  list.forEach((f) => {
    if (maxFiles != null && selectedFiles.length >= maxFiles) return;
    const isPdf = f.type === 'application/pdf' || (f.name && f.name.toLowerCase().endsWith('.pdf'));
    const isImg = (f.type && f.type.startsWith('image/')) || /\.(jpe?g|png|gif|webp)$/i.test(f.name || '');
    if (isPdfAccept && isPdf) selectedFiles.push(f);
    else if (isImageAccept && isImg) selectedFiles.push(f);
  });
  dropZone.classList.add('has-files');
  fileCardsWrap?.classList.add('has-files');
  dropText.textContent = `${selectedFiles.length} files selected`;
  updateSubmitButton();
  updateFileVizVisibility();
  renderFileCards();
}

function updateFileVizVisibility() {
  const hasFiles = selectedFiles.length > 0;
  const multi = currentTool?.multi;
  const orderMatters = currentTool?.orderMatters;
  const maxFiles = currentTool?.maxFiles;
  const atMaxFiles = maxFiles != null && selectedFiles.length >= maxFiles;
  if (fileVizInstruction) {
    fileVizInstruction.classList.toggle('hidden', !hasFiles || !orderMatters);
  }
  if (fileVizActions) {
    fileVizActions.classList.toggle('hidden', !hasFiles || !multi);
  }
  if (addMoreBtn) {
    addMoreBtn.classList.toggle('hidden', atMaxFiles);
  }
  if (sortBtnAZ) sortBtnAZ.classList.toggle('hidden', !orderMatters);
  if (sortBtnZA) sortBtnZA.classList.toggle('hidden', !orderMatters);
  if (addMoreBadge) {
    addMoreBadge.textContent = selectedFiles.length;
  }
}

function isPdfFile(file) {
  return file.type === 'application/pdf' || (file.name && file.name.toLowerCase().endsWith('.pdf'));
}

function isImageFile(file) {
  return (file.type && file.type.startsWith('image/')) || /\.(jpe?g|png|gif|webp)$/i.test(file.name || '');
}

async function generatePdfThumbnail(file) {
  if (typeof pdfjsLib === 'undefined') return null;
  try {
    const buf = await file.arrayBuffer();
    const doc = await pdfjsLib.getDocument({ data: buf }).promise;
    const page = await doc.getPage(1);
    const viewport1 = page.getViewport({ scale: 1 });
    const scale = Math.min(200 / viewport1.width, 260 / viewport1.height, 2);
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    await page.render({ canvasContext: ctx, viewport }).promise;
    return canvas;
  } catch (_) {
    return null;
  }
}

function createFileCard(file, thumbNode, index, draggable) {
  const card = document.createElement('div');
  card.className = 'file-card' + (draggable ? ' draggable' : '');
  card.dataset.index = String(index);
  card.setAttribute('draggable', draggable ? 'true' : 'false');
  const thumbWrap = document.createElement('div');
  thumbWrap.className = 'file-card-thumb';
  if (thumbNode) {
    thumbNode.setAttribute('draggable', 'false');
    thumbNode.style.pointerEvents = 'none';
    thumbWrap.appendChild(thumbNode);
  } else {
    const placeholder = document.createElement('div');
    placeholder.className = 'file-card-thumb-placeholder';
    placeholder.textContent = '📄';
    thumbWrap.appendChild(placeholder);
  }
  const actions = document.createElement('div');
  actions.className = 'file-card-actions';
  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.className = 'file-card-delete';
  deleteBtn.title = 'Remove file';
  deleteBtn.setAttribute('aria-label', 'Remove file');
  deleteBtn.innerHTML = '×';
  deleteBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    removeFileAtIndex(parseInt(card.dataset.index, 10));
  });
  actions.appendChild(deleteBtn);
  if (draggable) {
    const handle = document.createElement('span');
    handle.className = 'file-card-drag-handle';
    handle.title = 'Drag to reorder';
    handle.setAttribute('aria-label', 'Drag to reorder');
    handle.textContent = '⋮⋮';
    actions.appendChild(handle);
  }
  const name = document.createElement('div');
  name.className = 'file-card-name';
  name.title = file.name;
  name.textContent = file.name;
  card.appendChild(thumbWrap);
  card.appendChild(actions);
  card.appendChild(name);
  return card;
}

function removeFileAtIndex(index) {
  if (index < 0 || index >= selectedFiles.length) return;
  selectedFiles.splice(index, 1);
  if (selectedFiles.length === 0) {
    dropZone.classList.remove('has-files');
    fileCardsWrap?.classList.remove('has-files');
    dropText.textContent = currentTool?.dropText || 'Drop files here';
    lastPreviewJobId = null;
    lastCompareJobId = null;
    document.querySelector('.view-tab[data-view="preview"]')?.classList.remove('has-preview');
    if (previewViewIframe) {
      previewViewIframe.src = '';
      previewViewIframe.classList.add('hidden');
    }
    if (previewViewEmpty) previewViewEmpty.classList.remove('hidden');
    hideJobPanel();
  } else {
    dropText.textContent = selectedFiles.length === 1 ? selectedFiles[0].name : `${selectedFiles.length} files selected`;
  }
  updateSubmitButton();
  updateFileVizVisibility();
  renderFileCards();
}

async function renderFileCards() {
  if (!fileCards) return;
  fileCards.innerHTML = '';
  const multi = currentTool?.multi;
  const draggable = multi && selectedFiles.length > 1;
  for (let i = 0; i < selectedFiles.length; i++) {
    const file = selectedFiles[i];
    let thumbNode = null;
    if (isPdfFile(file)) {
      const canvas = await generatePdfThumbnail(file);
      if (canvas) {
        thumbNode = canvas;
      }
    } else if (isImageFile(file)) {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.alt = file.name;
      thumbNode = img;
    }
    const card = createFileCard(file, thumbNode, i, draggable);
    fileCards.appendChild(card);
  }
  setupCardDragAndDrop();
}

function setupCardDragAndDrop() {
  if (!fileCards || !currentTool?.multi) return;
  let draggedIndex = null;
  fileCards.querySelectorAll('.file-card.draggable').forEach((card) => {
    card.addEventListener('dragstart', (e) => {
      if (e.target.closest('.file-card-delete')) return;
      draggedIndex = parseInt(card.dataset.index, 10);
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', String(draggedIndex));
      e.dataTransfer.setData('application/x-pdf-editor-index', String(draggedIndex));
      card.classList.add('dragging');
      if (e.dataTransfer.setDragImage) {
        const rect = card.getBoundingClientRect();
        e.dataTransfer.setDragImage(card, rect.width / 2, rect.height / 2);
      }
    });
    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      fileCards.querySelectorAll('.file-card').forEach((c) => c.classList.remove('drag-over'));
      draggedIndex = null;
    });
    card.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      const toIndex = parseInt(card.dataset.index, 10);
      if (draggedIndex !== null && toIndex !== draggedIndex) card.classList.add('drag-over');
    });
    card.addEventListener('dragleave', () => card.classList.remove('drag-over'));
    card.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      card.classList.remove('drag-over');
      const from = parseInt(e.dataTransfer.getData('text/plain') || e.dataTransfer.getData('application/x-pdf-editor-index'), 10);
      const to = parseInt(card.dataset.index, 10);
      if (from === to || isNaN(from) || isNaN(to)) return;
      const f = selectedFiles[from];
      selectedFiles.splice(from, 1);
      selectedFiles.splice(to, 0, f);
      updateSubmitButton();
      addMoreBadge.textContent = selectedFiles.length;
      renderFileCards();
    });
  });
}
function updateSubmitButton() {
  const minFiles = currentTool?.minFiles || (currentTool?.multi ? 1 : 1);
  let filesOk = selectedFiles.length >= minFiles;
  if (currentTool?.allowUrlAsAlternative) {
    const urlVal = (document.querySelector('#opt-url')?.value || '').trim();
    filesOk = filesOk || urlVal.length > 0;
  }
  let extraOk = true;
  if (currentTool?.extraFiles) {
    for (const ef of currentTool.extraFiles) {
      if (ef.required) {
        const el = document.querySelector(`#extra-${ef.name}`);
        if (!el?.files?.length) { extraOk = false; break; }
      }
    }
  }
  // Sanitize: at least one option must be selected
  if (currentTool?.title === 'Sanitize PDF' && currentTool?.options?.length) {
    const params = getOptionParams();
    const sanitizeOpts = ['remove_javascript', 'remove_embedded_files', 'remove_xmp_metadata', 'remove_document_metadata', 'remove_links', 'remove_fonts'];
    const anySelected = sanitizeOpts.some((k) => params[k] === true || params[k] === 'true');
    if (!anySelected) extraOk = false;
  }
  submitBtn.disabled = !(filesOk && extraOk);
}

function setupDropZone() {
  // When file input is clicked, dialog opens. After a short delay, move focus to drop zone
  // so that closing the dialog without selecting doesn't refocus the input and re-open it.
  fileInput.addEventListener('click', () => {
    setTimeout(() => {
      fileInput.blur();
      dropZone.focus();
    }, 300);
  });
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    setFiles(e.dataTransfer.files);
  });
  fileInput.addEventListener('change', () => {
    if (addMoreMode) {
      appendFiles(fileInput.files);
      addMoreMode = false;
      fileInput.value = '';
    } else {
      setFiles(fileInput.files);
    }
  });

  if (addMoreBtn) {
    addMoreBtn.addEventListener('click', (e) => {
      e.preventDefault();
      if (currentTool?.multi) {
        addMoreMode = true;
        fileInput.click();
      }
    });
  }
  if (sortBtnAZ) {
    sortBtnAZ.addEventListener('click', () => {
      if (!currentTool?.multi || selectedFiles.length < 2) return;
      selectedFiles.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));
      renderFileCards();
    });
  }
  if (sortBtnZA) {
    sortBtnZA.addEventListener('click', () => {
      if (!currentTool?.multi || selectedFiles.length < 2) return;
      selectedFiles.sort((a, b) => b.name.localeCompare(a.name, undefined, { sensitivity: 'base' }));
      renderFileCards();
    });
  }

  if (fileCardsWrap) {
    fileCardsWrap.addEventListener('dragover', (e) => {
      if (selectedFiles.length > 0 && currentTool?.multi) {
        e.preventDefault();
        e.stopPropagation();
        fileCardsWrap.classList.add('drag-over');
      }
    });
    fileCardsWrap.addEventListener('dragleave', (e) => {
      if (!fileCardsWrap.contains(e.relatedTarget)) fileCardsWrap.classList.remove('drag-over');
    });
    fileCardsWrap.addEventListener('drop', (e) => {
      fileCardsWrap.classList.remove('drag-over');
      if (selectedFiles.length > 0 && currentTool?.multi && e.dataTransfer.files.length) {
        e.preventDefault();
        e.stopPropagation();
        appendFiles(e.dataTransfer.files);
      }
    });
  }
}

// ----- Job & download -----
function hideJobPanel() {
  jobPanel.classList.add('hidden');
  jobStatus.textContent = '';
  jobStatus.className = 'job-status';
  downloadBtn.classList.add('hidden');
  downloadBtn.href = '#';
  if (uploadNewFileBtn) uploadNewFileBtn.classList.add('hidden');
  if (openCompareViewBtn) openCompareViewBtn.classList.add('hidden');
}

function showJobPanel(statusText, state = 'pending', _jobId = null) {
  jobPanel.classList.remove('hidden');
  jobStatus.textContent = statusText;
  jobStatus.className = 'job-status ' + state;
  if (uploadNewFileBtn) {
    uploadNewFileBtn.classList.toggle('hidden', state !== 'completed' && state !== 'failed');
  }
}

function pollJob(jobId) {
  showJobPanel('Processing…', 'processing');
  const interval = setInterval(async () => {
    try {
      const job = await API.get(`/jobs/${jobId}`);
      if (job.status === 'completed') {
        clearInterval(interval);
        lastPreviewJobId = jobId;
        showJobPanel('Ready! Click below to download.', 'completed', jobId);
        downloadBtn.classList.remove('hidden');
        downloadBtn.href = `${API.base}/download/${jobId}`;
        downloadBtn.download = job.output_filename || 'result.pdf';
        document.querySelector('.view-tab[data-view="preview"]')?.classList.add('has-preview');
        if (job.job_type === 'compare_pdf') {
          lastCompareJobId = jobId;
          if (openCompareViewBtn) {
            openCompareViewBtn.classList.remove('hidden');
          }
        } else if (openCompareViewBtn) {
          openCompareViewBtn.classList.add('hidden');
        }
        if (job.params?.redaction_warning) {
          toast(job.params.redaction_warning, false);
        }
      } else if (job.status === 'failed') {
        clearInterval(interval);
        showJobPanel('Failed: ' + (job.error || 'Unknown error'), 'failed');
        toast(job.error || 'Job failed', true);
        submitBtn.disabled = false;
        if (openCompareViewBtn) openCompareViewBtn.classList.add('hidden');
      }
    } catch (e) {
      clearInterval(interval);
      showJobPanel('Error checking status.', 'failed');
      toast(e.message, true);
    }
  }, 800);
}

async function submitJob() {
  if (!currentTool) return;
  const params = getOptionParams();
  const canSubmitWithUrl = currentTool.allowUrlAsAlternative && (params?.url || '').trim().length > 0;
  if (!canSubmitWithUrl && !selectedFiles.length) return;
  if (!canSubmitWithUrl && currentTool.minFiles && selectedFiles.length < currentTool.minFiles) return;
  lastPreviewJobId = null;
  document.querySelector('.view-tab[data-view="preview"]')?.classList.remove('has-preview');
  if (previewViewIframe) previewViewIframe.src = '';
  if (previewViewEmpty) previewViewEmpty.classList.remove('hidden');
  if (previewViewIframe) previewViewIframe.classList.add('hidden');
  if (currentTool.extraFiles) {
    const extra = getOptionFiles();
    for (const ef of currentTool.extraFiles) {
      if (ef.required && !extra[ef.name]) {
        toast(`Please add ${ef.label}`, true);
        return;
      }
    }
  }
  if (currentTool?.title === 'Sanitize PDF' && currentTool?.options?.length) {
    const sanitizeOpts = ['remove_javascript', 'remove_embedded_files', 'remove_xmp_metadata', 'remove_document_metadata', 'remove_links', 'remove_fonts'];
    const anySelected = sanitizeOpts.some((k) => params[k] === true || params[k] === 'true');
    if (!anySelected) {
      toast('Select at least one sanitisation option.', true);
      return;
    }
  }
  submitBtn.disabled = true;
  try {
    const extraFiles = getOptionFiles();
    const result = await currentTool.submit(selectedFiles, params, extraFiles);
    if (currentTool.syncResponse) {
      showJobPanel('', 'completed');
      jobStatus.innerHTML = '<pre class="sync-result">' + escapeHtml(JSON.stringify(result, null, 2)) + '</pre>';
      downloadBtn.classList.add('hidden');
    } else {
      pollJob(result.job_id);
    }
  } catch (e) {
    toast(e.message, true);
    submitBtn.disabled = false;
  }
}
function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// ----- Compare view -----
let compareReportData = null;
let compareZoomLevel = 1;
let compareRerender = null;

async function openCompareView(jobId) {
  if (!jobId || !compareView || typeof pdfjsLib === 'undefined') return;
  compareCanvasWrapLeft.innerHTML = '';
  compareCanvasWrapRight.innerHTML = '';
  compareReportList.innerHTML = '';
  compareReportCount.textContent = '0';
  compareReportSearch.value = '';
  compareDownloadReportBtn.style.display = 'none';

  const base = API.base || '';
  const leftUrl = `${base}/compare/${jobId}/left`;
  const rightUrl = `${base}/compare/${jobId}/right`;
  const reportUrl = `${base}/compare/${jobId}/report`;

  try {
    setView('compare');
    compareCanvasWrapLeft.textContent = 'Loading…';
    compareCanvasWrapRight.textContent = 'Loading…';
    compareCanvasWrapLeft.classList.add('is-loading');
    compareCanvasWrapRight.classList.add('is-loading');

    const [reportRes, leftDoc, rightDoc] = await Promise.all([
      fetch(reportUrl).then((r) => (r.ok ? r.json() : { changes: [] })),
      pdfjsLib.getDocument(leftUrl).promise,
      pdfjsLib.getDocument(rightUrl).promise,
    ]);

    compareReportData = reportRes;
    const changes = reportRes.changes || [];
    compareReportCount.textContent = String(changes.length);
    compareDownloadReportBtn.style.display = 'inline-block';
    compareDownloadReportBtn.download = 'compare_report.json';
    compareDownloadReportBtn.href = URL.createObjectURL(new Blob([JSON.stringify(reportRes, null, 2)], { type: 'application/json' }));

    function renderReportList(filter) {
      const q = (filter || '').trim().toLowerCase();
      const list = document.getElementById('compareReportList');
      if (!list) return;
      list.innerHTML = '';
      changes.forEach((c) => {
        if (q && !(c.text || '').toLowerCase().includes(q)) return;
        const el = document.createElement('div');
        el.className = 'compare-report-item type-' + c.type;
        el.innerHTML = '<div class="compare-report-item-page">Page ' + c.page + ' — ' + (c.type === 'remove' ? 'Removed' : 'Added') + '</div>' + escapeHtml((c.text || '').slice(0, 500) + (c.text && c.text.length > 500 ? '…' : ''));
        list.appendChild(el);
      });
    }
    renderReportList('');
    if (compareReportSearch) {
      compareReportSearch.oninput = () => renderReportList(compareReportSearch.value);
    }

    await new Promise((r) => requestAnimationFrame(r));
    const padding = 32;
    const wrapWidth = Math.max(200, (compareCanvasWrapLeft.clientWidth || 400) - padding);
    const wrapHeight = Math.max(300, (compareCanvasWrapLeft.clientHeight || 500) - padding);
    const firstPageLeft = await leftDoc.getPage(1);
    const baseViewport = firstPageLeft.getViewport({ scale: 1 });
    const scaleX = wrapWidth / baseViewport.width;
    const scaleY = wrapHeight / baseViewport.height;
    const baseScale = Math.min(scaleX, scaleY, 2);
    compareZoomLevel = 1;
    if (compareZoomLabel) compareZoomLabel.textContent = '100%';

    async function renderPdfToWrap(doc, wrap, scale) {
      wrap.innerHTML = '';
      wrap.classList.remove('is-loading');
      const inner = document.createElement('div');
      inner.className = 'compare-pane-canvas-inner';
      const numPages = doc.numPages;
      for (let i = 1; i <= numPages; i++) {
        const page = await doc.getPage(i);
        const viewport = page.getViewport({ scale });
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        await page.render({ canvasContext: ctx, viewport }).promise;
        inner.appendChild(canvas);
      }
      wrap.appendChild(inner);
    }

    async function renderBoth() {
      const scale = baseScale * compareZoomLevel;
      await Promise.all([
        renderPdfToWrap(leftDoc, compareCanvasWrapLeft, scale),
        renderPdfToWrap(rightDoc, compareCanvasWrapRight, scale),
      ]);
    }

    compareRerender = () => renderBoth();

    await renderBoth();

    let syncingScroll = false;
    function syncScroll(source, target) {
      if (!compareScrollSync?.checked) return;
      if (syncingScroll) return;
      syncingScroll = true;
      const scrollHeightSource = source.scrollHeight - source.clientHeight;
      const scrollHeightTarget = target.scrollHeight - target.clientHeight;
      if (scrollHeightSource > 0 && scrollHeightTarget > 0) {
        const ratio = source.scrollTop / scrollHeightSource;
        target.scrollTop = Math.round(ratio * scrollHeightTarget);
      } else {
        target.scrollTop = source.scrollTop;
      }
      const scrollWidthSource = source.scrollWidth - source.clientWidth;
      const scrollWidthTarget = target.scrollWidth - target.clientWidth;
      if (scrollWidthSource > 0 && scrollWidthTarget > 0) {
        const ratioX = source.scrollLeft / scrollWidthSource;
        target.scrollLeft = Math.round(ratioX * scrollWidthTarget);
      } else {
        target.scrollLeft = source.scrollLeft;
      }
      syncingScroll = false;
    }
    compareCanvasWrapLeft.addEventListener('scroll', () => syncScroll(compareCanvasWrapLeft, compareCanvasWrapRight));
    compareCanvasWrapRight.addEventListener('scroll', () => syncScroll(compareCanvasWrapRight, compareCanvasWrapLeft));
  } catch (e) {
    toast(e.message || 'Failed to open compare view', true);
  }
}

// ----- Events -----
document.querySelectorAll('.nav-tool').forEach((btn) => {
  btn.addEventListener('click', () => showWorkspace(btn.dataset.tool));
});
const optFlattenOnlyForms = document.getElementById('opt-flatten_only_forms');
if (optFlattenOnlyForms) optFlattenOnlyForms.addEventListener('change', updateSubmitButton);

backBtn.addEventListener('click', showHome);

if (toolSearch) {
  toolSearch.addEventListener('input', () => {
    const q = (toolSearch.value || '').trim().toLowerCase();
    document.querySelectorAll('.nav-category').forEach((cat) => {
      const tools = cat.querySelectorAll('.nav-tool');
      let visible = 0;
      tools.forEach((t) => {
        const name = (t.querySelector('.nav-tool-name')?.textContent || t.textContent || '').toLowerCase();
        const match = !q || name.includes(q);
        t.classList.toggle('hidden-by-search', !match);
        if (match) visible++;
      });
      cat.style.display = visible > 0 ? '' : 'none';
    });
  });
}

document.querySelectorAll('.nav-category-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const expanded = btn.getAttribute('aria-expanded') !== 'false';
    btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
  });
});

const homeCard = document.getElementById('homeCard');
if (homeCard) {
  homeCard.addEventListener('dragover', (e) => {
    e.preventDefault();
    homeCard.classList.add('drag-over');
  });
  homeCard.addEventListener('dragleave', () => homeCard.classList.remove('drag-over'));
  homeCard.addEventListener('drop', (e) => {
    e.preventDefault();
    homeCard.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      toast('Select a tool from the sidebar first, then add your files.', false);
    }
  });
}

if (sidebarToggle && sidebar) {
  sidebarToggle.addEventListener('click', () => {
    const open = sidebar.classList.toggle('sidebar-open');
    sidebarToggle.setAttribute('aria-expanded', open);
    sidebarToggle.setAttribute('aria-label', open ? 'Close tools menu' : 'Open tools menu');
  });
  document.addEventListener('click', (e) => {
    if (sidebar.classList.contains('sidebar-open') && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
      sidebar.classList.remove('sidebar-open');
      sidebarToggle.setAttribute('aria-expanded', 'false');
      sidebarToggle.setAttribute('aria-label', 'Open tools menu');
    }
  });
}
submitBtn.addEventListener('click', submitJob);
if (uploadNewFileBtn) uploadNewFileBtn.addEventListener('click', clearFiles);
if (openCompareViewBtn) openCompareViewBtn.addEventListener('click', () => { if (lastCompareJobId) openCompareView(lastCompareJobId); });
if (compareViewBackBtn) compareViewBackBtn.addEventListener('click', () => { setView('tools'); compareRerender = null; });
if (compareZoomIn) {
  compareZoomIn.addEventListener('click', () => {
    compareZoomLevel = Math.min(3, compareZoomLevel + 0.25);
    if (compareZoomLabel) compareZoomLabel.textContent = Math.round(compareZoomLevel * 100) + '%';
    if (compareRerender) compareRerender();
  });
}
if (compareZoomOut) {
  compareZoomOut.addEventListener('click', () => {
    compareZoomLevel = Math.max(0.5, compareZoomLevel - 0.25);
    if (compareZoomLabel) compareZoomLabel.textContent = Math.round(compareZoomLevel * 100) + '%';
    if (compareRerender) compareRerender();
  });
}

setupDropZone();

initTheme();
initView();

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    setTheme(next);
  });
}

document.querySelectorAll('.view-tab').forEach((tab) => {
  tab.addEventListener('click', () => setView(tab.dataset.view));
});
