/**
 * AI Document Scanner — Insurance Application Forms
 * insurance_broker_suite/static/src/js/ai_doc_scanner.js
 *
 * Adds camera/upload scan buttons to each form section.
 * Sends captured images to /insurance/ai/scan-document and
 * auto-fills matched form fields.
 */
(function () {
    'use strict';

    // ── Configuration ─────────────────────────────────────────────────────────

    /** Map each form section (by CSS class on .o_ins_form_section) → scan config */
    const SECTION_CONFIGS = [
        {
            // Personal Information section (always present)
            titleMatch: /personal information/i,
            scanGroup:  'personal',
            label:      'Scan ID / Passport',
            docTypes:   [
                { value: 'passport',  label: '🛂 Passport' },
                { value: 'id_card',   label: '🪪 National ID' },
            ],
            defaultDoc: 'id_card',
        },
        {
            // Motor / Vehicle section
            titleMatch: /vehicle information/i,
            scanGroup:  'motor',
            label:      'Scan Car Documents',
            docTypes:   [
                { value: 'car_registration', label: '🚗 Registration Card' },
                { value: 'driving_license',  label: '🪪 Driving Licence' },
            ],
            defaultDoc: 'car_registration',
        },
        {
            // Medical section
            titleMatch: /medical/i,
            scanGroup:  'medical',
            label:      'Scan Health Card',
            docTypes:   [
                { value: 'health_card', label: '💊 Health / Medical Card' },
                { value: 'id_card',     label: '🪪 National ID' },
            ],
            defaultDoc: 'health_card',
        },
    ];

    // ── State ─────────────────────────────────────────────────────────────────
    let stream       = null;   // MediaStream from camera
    let capturedBlob = null;   // Last captured image Blob
    let activeConfig = null;   // Current SECTION_CONFIGS entry
    let activeDocType = null;  // Selected document type string

    // ── DOM References ────────────────────────────────────────────────────────
    let modal, video, canvas, previewImg, placeholder, scanFrame, scanLine;
    let statusEl, resultPreview, fileInput;
    let btnCapture, btnRetake, btnUpload, btnAnalyze, btnClose;

    // ── Helpers ───────────────────────────────────────────────────────────────

    function getCsrfToken() {
        const el = document.querySelector('input[name="csrf_token"]');
        return el ? el.value : '';
    }

    function blobToBase64(blob) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result); // data:...;base64,...
            reader.readAsDataURL(blob);
        });
    }

    function setStatus(type, message) {
        statusEl.className = `o_ins_scan_status show ${type}`;
        if (type === 'processing') {
            statusEl.innerHTML = `<span class="spinner"></span>${message}`;
        } else if (type === 'success') {
            statusEl.innerHTML = `<span>✓</span> ${message}`;
        } else {
            statusEl.innerHTML = `<span>✗</span> ${message}`;
        }
    }

    function clearStatus() {
        statusEl.className = 'o_ins_scan_status';
        statusEl.innerHTML = '';
    }

    function showPlaceholder() {
        placeholder.style.display = 'flex';
        video.classList.remove('active');
        canvas.classList.remove('active');
        previewImg.classList.remove('active');
        scanFrame.classList.remove('active');
        scanLine.classList.remove('active');
    }

    function showVideo() {
        placeholder.style.display = 'none';
        video.classList.add('active');
        canvas.classList.remove('active');
        previewImg.classList.remove('active');
        scanFrame.classList.add('active');
        scanLine.classList.add('active');
    }

    function showCanvas(dataUrl) {
        placeholder.style.display = 'none';
        video.classList.remove('active');
        canvas.classList.remove('active');
        previewImg.classList.add('active');
        previewImg.src = dataUrl;
        scanFrame.classList.remove('active');
        scanLine.classList.remove('active');
    }

    function updateDocTypePills(docTypes, defaultDoc) {
        const pillsContainer = modal.querySelector('.o_ins_doctype_pills');
        pillsContainer.innerHTML = '';
        docTypes.forEach((dt) => {
            const pill = document.createElement('button');
            pill.type = 'button';
            pill.className = 'o_ins_doctype_pill' + (dt.value === defaultDoc ? ' active' : '');
            pill.dataset.value = dt.value;
            pill.textContent = dt.label;
            pill.addEventListener('click', () => {
                pillsContainer.querySelectorAll('.o_ins_doctype_pill').forEach(p => p.classList.remove('active'));
                pill.classList.add('active');
                activeDocType = dt.value;
            });
            pillsContainer.appendChild(pill);
        });
        activeDocType = defaultDoc;
    }

    // ── Camera ────────────────────────────────────────────────────────────────

    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 960 } },
                audio: false,
            });
            video.srcObject = stream;
            await video.play();
            showVideo();
            btnCapture.style.display = 'flex';
            btnRetake.style.display  = 'none';
            btnAnalyze.style.display = 'none';
            clearStatus();
            capturedBlob = null;
        } catch (err) {
            setStatus('error', 'Camera not available. Please use the Upload button instead.');
        }
    }

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            stream = null;
        }
    }

    function captureFrame() {
        canvas.width  = video.videoWidth  || 640;
        canvas.height = video.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        canvas.toBlob((blob) => {
            capturedBlob = blob;
            const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
            stopCamera();
            showCanvas(dataUrl);
            btnCapture.style.display = 'none';
            btnRetake.style.display  = 'flex';
            btnAnalyze.style.display = 'flex';
            clearStatus();
        }, 'image/jpeg', 0.92);
    }

    // ── Modal open/close ──────────────────────────────────────────────────────

    function openModal(cfg) {
        activeConfig  = cfg;
        capturedBlob  = null;
        modal.querySelector('.o_ins_scan_header h5').textContent = cfg.label;
        updateDocTypePills(cfg.docTypes, cfg.defaultDoc);
        clearStatus();
        resultPreview.classList.remove('show');
        showPlaceholder();
        btnCapture.style.display = 'none';
        btnRetake.style.display  = 'none';
        btnAnalyze.style.display = 'none';
        modal.classList.add('o_ins_scan_open');
        // Auto-start camera
        startCamera();
    }

    function closeModal() {
        stopCamera();
        modal.classList.remove('o_ins_scan_open');
        showPlaceholder();
        capturedBlob  = null;
        activeConfig  = null;
    }

    // ── Analyse (send to backend) ─────────────────────────────────────────────

    async function analyseImage() {
        if (!capturedBlob) {
            setStatus('error', 'No image captured. Please capture or upload a document first.');
            return;
        }

        setStatus('processing', 'Analysing document with AI…');
        btnAnalyze.disabled = true;

        try {
            const base64 = await blobToBase64(capturedBlob);

            const response = await fetch('/insurance/ai/scan-document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method:  'call',
                    id:      1,
                    params: {
                        image_b64:     base64,
                        document_type: activeDocType,
                    },
                }),
            });

            const json = await response.json();
            const result = json.result;

            if (!result || !result.success) {
                const msg = result?.error || 'AI scan failed. Please try again.';
                setStatus('error', msg);
                return;
            }

            const fields = result.fields || {};
            const filled = fillFormFields(fields);

            if (filled > 0) {
                setStatus('success', `${filled} field(s) auto-filled successfully!`);
                renderResultPreview(fields);
                // Close modal after short delay
                setTimeout(() => closeModal(), 2200);
            } else {
                setStatus('error', 'No matching fields found. Please check the document type or fill manually.');
                renderResultPreview(result.raw || {});
            }

        } catch (err) {
            setStatus('error', `Error: ${err.message}`);
        } finally {
            btnAnalyze.disabled = false;
        }
    }

    // ── Form auto-fill ────────────────────────────────────────────────────────

    function fillFormFields(fields) {
        let count = 0;
        Object.entries(fields).forEach(([name, value]) => {
            if (!value) return;
            const el = document.querySelector(`.o_ins_form [name="${name}"]`);
            if (!el) return;
            el.value = value;
            el.classList.add('o_ins_field_filled');
            el.addEventListener('animationend', () => el.classList.remove('o_ins_field_filled'), { once: true });
            // Trigger change event so Odoo JS picks up the value
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('input',  { bubbles: true }));
            count++;
        });
        return count;
    }

    // ── Result preview table ──────────────────────────────────────────────────

    function renderResultPreview(data) {
        const rows = Object.entries(data)
            .filter(([, v]) => v)
            .map(([k, v]) => `<tr><td>${k.replace(/_/g, ' ')}</td><td>${v}</td></tr>`)
            .join('');

        if (!rows) { resultPreview.classList.remove('show'); return; }
        resultPreview.innerHTML = `<table>${rows}</table>`;
        resultPreview.classList.add('show');
    }

    // ── File upload ───────────────────────────────────────────────────────────

    function handleFileUpload(file) {
        if (!file || !file.type.startsWith('image/')) {
            setStatus('error', 'Please select a valid image file (JPG, PNG, WEBP).');
            return;
        }
        capturedBlob = file;
        const url = URL.createObjectURL(file);
        stopCamera();
        showCanvas(url);
        btnCapture.style.display = 'none';
        btnRetake.style.display  = 'flex';
        btnAnalyze.style.display = 'flex';
        clearStatus();
    }

    // ── Build modal HTML ──────────────────────────────────────────────────────

    function buildModal() {
        const div = document.createElement('div');
        div.id = 'o_ins_scan_modal';
        div.setAttribute('role', 'dialog');
        div.setAttribute('aria-modal', 'true');
        div.innerHTML = `
<div class="o_ins_scan_card">
  <div class="o_ins_scan_header">
    <h5>Scan Document</h5>
    <button class="o_ins_scan_close" id="o_ins_scan_close_btn" aria-label="Close">&times;</button>
  </div>
  <div class="o_ins_scan_body">

    <!-- Document type selector -->
    <div class="o_ins_doctype_pills"></div>

    <!-- Camera / preview area -->
    <div class="o_ins_camera_area">
      <video id="o_ins_cam_video" playsinline muted></video>
      <canvas id="o_ins_cam_canvas"></canvas>
      <img id="o_ins_cam_preview" alt="Captured document"/>
      <div class="o_ins_camera_placeholder" id="o_ins_cam_placeholder">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.8-10H4.2C3 5.5 2 6.5 2 7.7v8.6C2 17.5 3 18.5 4.2 18.5h15.6c1.2 0 2.2-1 2.2-2.2V7.7c0-1.2-1-2.2-2.2-2.2m0 10.8H4.2V7.7h15.6v8.6z"/>
        </svg>
        <p>Starting camera…</p>
      </div>
      <div class="o_ins_scan_frame" id="o_ins_scan_frame"></div>
      <div class="o_ins_scanline"   id="o_ins_scanline"></div>
    </div>

    <!-- Action buttons -->
    <div class="o_ins_scan_actions">
      <button type="button" class="btn btn-primary"         id="o_ins_btn_capture" style="display:none">
        📸 Capture
      </button>
      <button type="button" class="btn btn-outline-secondary" id="o_ins_btn_retake" style="display:none">
        🔄 Retake
      </button>
      <button type="button" class="btn btn-success"          id="o_ins_btn_analyze" style="display:none">
        🤖 Analyse &amp; Fill
      </button>
      <button type="button" class="btn btn-outline-primary"  id="o_ins_btn_upload">
        📁 Upload File
      </button>
    </div>

    <!-- Status bar -->
    <div class="o_ins_scan_status" id="o_ins_scan_status"></div>

    <!-- Extracted fields preview -->
    <div class="o_ins_scan_result_preview" id="o_ins_scan_result_preview"></div>

    <!-- Hidden file input -->
    <input type="file" id="o_ins_scan_file_input" accept="image/*" capture="environment"/>
  </div>
</div>`;
        document.body.appendChild(div);

        // Wire references
        modal       = div;
        video       = div.querySelector('#o_ins_cam_video');
        canvas      = div.querySelector('#o_ins_cam_canvas');
        previewImg  = div.querySelector('#o_ins_cam_preview');
        placeholder = div.querySelector('#o_ins_cam_placeholder');
        scanFrame   = div.querySelector('#o_ins_scan_frame');
        scanLine    = div.querySelector('#o_ins_scanline');
        statusEl    = div.querySelector('#o_ins_scan_status');
        resultPreview = div.querySelector('#o_ins_scan_result_preview');
        fileInput   = div.querySelector('#o_ins_scan_file_input');

        btnCapture  = div.querySelector('#o_ins_btn_capture');
        btnRetake   = div.querySelector('#o_ins_btn_retake');
        btnUpload   = div.querySelector('#o_ins_btn_upload');
        btnAnalyze  = div.querySelector('#o_ins_btn_analyze');
        btnClose    = div.querySelector('#o_ins_scan_close_btn');

        // Events
        btnClose.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
        btnCapture.addEventListener('click', captureFrame);
        btnRetake.addEventListener('click', () => {
            capturedBlob = null;
            resultPreview.classList.remove('show');
            clearStatus();
            startCamera();
        });
        btnAnalyze.addEventListener('click', analyseImage);
        btnUpload.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files[0]) {
                handleFileUpload(fileInput.files[0]);
                fileInput.value = '';
            }
        });

        // Keyboard close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('o_ins_scan_open')) closeModal();
        });
    }

    // ── Inject scan buttons into form sections ────────────────────────────────

    function injectScanButtons() {
        const form = document.querySelector('.o_ins_form');
        if (!form) return;

        const sections = form.querySelectorAll('.o_ins_form_section');
        sections.forEach((section) => {
            const titleEl = section.querySelector('.o_ins_form_section_title');
            if (!titleEl) return;

            const titleText = titleEl.textContent.trim();
            const cfg = SECTION_CONFIGS.find(c => c.titleMatch.test(titleText));
            if (!cfg) return;

            // Avoid double injection
            if (titleEl.querySelector('.o_ins_scan_btn')) return;

            const btn = document.createElement('button');
            btn.type      = 'button';
            btn.className = 'o_ins_scan_btn';
            btn.innerHTML = `
<svg class="o_ins_scan_icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12 3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.8-10H4.2C3 5.5 2 6.5 2 7.7v8.6C2 17.5 3 18.5 4.2 18.5h15.6c1.2 0 2.2-1 2.2-2.2V7.7c0-1.2-1-2.2-2.2-2.2z"/>
</svg>
${cfg.label}`;
            btn.title = `Scan document with AI to auto-fill ${titleText} fields`;
            btn.addEventListener('click', () => openModal(cfg));

            titleEl.appendChild(btn);
        });
    }

    // ── Bootstrap ─────────────────────────────────────────────────────────────

    function init() {
        // Only activate on insurance application form pages
        if (!document.querySelector('.o_ins_form')) return;

        buildModal();
        injectScanButtons();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

}());
