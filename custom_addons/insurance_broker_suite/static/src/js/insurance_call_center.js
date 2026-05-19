/* ══════════════════════════════════════════════════════════════════
   Ameen Hub — AI Call Center Widget
   NEW FILE — insurance_broker_suite/static/src/js/insurance_call_center.js
   ══════════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    const CC = {
        sessionId: null,
        isRecording: false,
        mediaRecorder: null,
        audioChunks: [],
        uploadedFiles: [],

        // ── INIT ───────────────────────────────────────────────────────
        init() {
            this.sessionId = 'cc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            this.bindEvents();
            this.addWelcomeMessages();
        },

        bindEvents() {
            // Open triggers
            document.querySelectorAll('[data-open-cc]').forEach(el => {
                el.addEventListener('click', () => this.open());
            });

            // Close
            const closeBtn = document.getElementById('oCCClose');
            if (closeBtn) closeBtn.addEventListener('click', () => this.close());

            // Overlay backdrop click
            const overlay = document.getElementById('oCCOverlay');
            if (overlay) {
                overlay.addEventListener('click', e => {
                    if (e.target === overlay) this.close();
                });
            }

            // Tabs
            document.querySelectorAll('.o_cc_tab_btn').forEach(btn => {
                btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
            });

            // Chat send button & Enter key
            const sendBtn = document.getElementById('oCCSend');
            const chatInput = document.getElementById('oCCInput');
            if (sendBtn) sendBtn.addEventListener('click', () => this.sendMessage());
            if (chatInput) {
                chatInput.addEventListener('keydown', e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this.sendMessage();
                    }
                    this.autoResize(chatInput);
                });
                chatInput.addEventListener('input', () => this.autoResize(chatInput));
            }

            // Voice record button
            const recordBtn = document.getElementById('oCCRecord');
            if (recordBtn) recordBtn.addEventListener('click', () => this.toggleRecording());

            // File drop zone
            const dropZone = document.getElementById('oCCDropZone');
            const fileInput = document.getElementById('oCCFileInput');
            if (dropZone) {
                dropZone.addEventListener('click', () => fileInput && fileInput.click());
                dropZone.addEventListener('dragover', e => {
                    e.preventDefault();
                    dropZone.classList.add('dragover');
                });
                dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
                dropZone.addEventListener('drop', e => {
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                    this.handleFiles(e.dataTransfer.files);
                });
            }
            if (fileInput) {
                fileInput.addEventListener('change', () => {
                    this.handleFiles(fileInput.files);
                    fileInput.value = '';
                });
            }

            // Send files button
            const sendFilesBtn = document.getElementById('oCCSendFiles');
            if (sendFilesBtn) {
                sendFilesBtn.addEventListener('click', () => this.sendFilesAsMessage());
            }

            // Escape key closes
            document.addEventListener('keydown', e => {
                if (e.key === 'Escape') this.close();
            });
        },

        autoResize(el) {
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 100) + 'px';
        },

        // ── OPEN / CLOSE ────────────────────────────────────────────────
        open() {
            const overlay = document.getElementById('oCCOverlay');
            if (overlay) overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
            setTimeout(() => {
                const input = document.getElementById('oCCInput');
                if (input) input.focus();
            }, 350);
        },

        close() {
            const overlay = document.getElementById('oCCOverlay');
            if (overlay) overlay.classList.remove('active');
            document.body.style.overflow = '';
            if (this.isRecording) this.stopRecording();
        },

        // ── TABS ────────────────────────────────────────────────────────
        switchTab(tab) {
            document.querySelectorAll('.o_cc_tab_btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.o_cc_tab_pane').forEach(p => p.classList.remove('active'));
            const btn = document.querySelector(`.o_cc_tab_btn[data-tab="${tab}"]`);
            const pane = document.getElementById('oCCTab_' + tab);
            if (btn) btn.classList.add('active');
            if (pane) pane.classList.add('active');
        },

        // ── WELCOME MESSAGES ────────────────────────────────────────────
        addWelcomeMessages() {
            const msgs = [
                'مرحباً! أنا **أمين**، مساعدك الذكي لخدمات التأمين.',
                'Hello! I\'m **Ameen**, your AI Insurance Expert. 🛡️',
                'I can help you with **52 insurance products** — motor, medical, life, property, marine, engineering, cyber, and more.',
                'What can I help you with today?'
            ];
            msgs.forEach((msg, i) => {
                setTimeout(() => this.appendMessage('agent', msg), i * 500);
            });
            setTimeout(() => {
                this.appendQuickReplies([
                    '🚗 Motor Insurance',
                    '🏥 Medical Insurance',
                    '❤️ Life Insurance',
                    '🏠 Property Insurance',
                    '📋 Get a Quote',
                    '📂 Track My Application'
                ]);
            }, msgs.length * 500 + 300);
        },

        // ── CHAT ────────────────────────────────────────────────────────
        async sendMessage(text) {
            const input = document.getElementById('oCCInput');
            const message = (text || (input && input.value.trim()));
            if (!message) return;
            if (input) { input.value = ''; input.style.height = 'auto'; }

            // Remove any existing quick replies
            document.querySelectorAll('.o_cc_quick_replies').forEach(el => el.remove());

            this.appendMessage('user', message);
            this.showTyping(true);

            try {
                const resp = await fetch('/insurance/ai-chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: this.sessionId,
                        files: this.uploadedFiles.map(f => f.name),
                    }),
                });

                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                const data = await resp.json();

                this.showTyping(false);

                if (data.reply) this.appendMessage('agent', data.reply);
                if (data.quick_replies && data.quick_replies.length) {
                    this.appendQuickReplies(data.quick_replies);
                }

            } catch (err) {
                this.showTyping(false);
                this.appendMessage('agent',
                    'Sorry, I\'m having a connection issue right now. 😔\n\nPlease try again or call us directly:\n**📞 +968 2400 0000**'
                );
            }
        },

        appendMessage(role, text) {
            const container = document.getElementById('oCCMessages');
            if (!container) return;

            const isAgent = (role === 'agent');
            const div = document.createElement('div');
            div.className = 'o_cc_msg ' + (isAgent ? 'agent' : 'user');

            const formatted = text
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');

            if (isAgent) {
                div.innerHTML =
                    '<div class="o_cc_msg_avatar"><i class="fa fa-headphones"></i></div>' +
                    '<div class="o_cc_msg_bubble">' + formatted + '</div>';
            } else {
                div.innerHTML =
                    '<div class="o_cc_msg_bubble">' + formatted + '</div>' +
                    '<div class="o_cc_msg_avatar user"><i class="fa fa-user"></i></div>';
            }

            container.appendChild(div);
            requestAnimationFrame(() => div.classList.add('visible'));
            container.scrollTop = container.scrollHeight;
        },

        appendQuickReplies(replies) {
            const container = document.getElementById('oCCMessages');
            if (!container) return;

            const wrap = document.createElement('div');
            wrap.className = 'o_cc_quick_replies';

            replies.forEach(reply => {
                const btn = document.createElement('button');
                btn.className = 'o_cc_quick_btn';
                btn.textContent = reply;
                btn.addEventListener('click', () => {
                    wrap.remove();
                    this.sendMessage(reply);
                });
                wrap.appendChild(btn);
            });

            container.appendChild(wrap);
            container.scrollTop = container.scrollHeight;
        },

        showTyping(show) {
            const container = document.getElementById('oCCMessages');
            if (!container) return;
            let indicator = document.getElementById('oCCTyping');

            if (show) {
                if (!indicator) {
                    indicator = document.createElement('div');
                    indicator.id = 'oCCTyping';
                    indicator.className = 'o_cc_msg agent typing';
                    indicator.innerHTML =
                        '<div class="o_cc_msg_avatar"><i class="fa fa-headphones"></i></div>' +
                        '<div class="o_cc_msg_bubble">' +
                        '<span class="o_cc_dot"></span>' +
                        '<span class="o_cc_dot"></span>' +
                        '<span class="o_cc_dot"></span>' +
                        '</div>';
                    container.appendChild(indicator);
                    requestAnimationFrame(() => indicator.classList.add('visible'));
                }
            } else {
                if (indicator) indicator.remove();
            }
            container.scrollTop = container.scrollHeight;
        },

        // ── VOICE RECORDING ─────────────────────────────────────────────
        async toggleRecording() {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                await this.startRecording();
            }
        },

        async startRecording() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.audioChunks = [];
                this.mediaRecorder = new MediaRecorder(stream);

                this.mediaRecorder.ondataavailable = e => {
                    if (e.data.size > 0) this.audioChunks.push(e.data);
                };
                this.mediaRecorder.onstop = () => {
                    const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
                    this.onRecordingComplete(blob);
                    stream.getTracks().forEach(t => t.stop());
                };

                this.mediaRecorder.start(100);
                this.isRecording = true;
                this.setRecordUI(true);
                this.startWaveAnimation();
            } catch (err) {
                this.setTranscript(
                    '<span class="text-danger"><i class="fa fa-exclamation-triangle me-1"></i>' +
                    'Microphone access denied. Please allow microphone permissions.</span>'
                );
            }
        },

        stopRecording() {
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            this.isRecording = false;
            this.setRecordUI(false);
            this.stopWaveAnimation();
        },

        setRecordUI(recording) {
            const btn = document.getElementById('oCCRecord');
            const status = document.getElementById('oCCVoiceStatus');
            if (btn) {
                btn.classList.toggle('recording', recording);
                btn.innerHTML = recording
                    ? '<i class="fa fa-stop"></i>'
                    : '<i class="fa fa-microphone"></i>';
            }
            if (status) {
                status.textContent = recording
                    ? 'Recording… tap to stop'
                    : 'Tap the microphone to start speaking';
            }
        },

        onRecordingComplete(blob) {
            const sizeKB = (blob.size / 1024).toFixed(1);
            this.setTranscript(
                '<div class="o_cc_voice_recorded">' +
                '<i class="fa fa-check-circle text-success me-2"></i>' +
                '<strong>Voice message recorded</strong> (' + sizeKB + ' KB)<br>' +
                '<small class="text-muted">Your message will be transcribed and processed by the AI agent.</small>' +
                '<div class="mt-3 d-flex gap-2 justify-content-center">' +
                '<button class="btn btn-primary btn-sm" id="oCCSendVoice">' +
                '<i class="fa fa-send me-1"></i> Send Voice Message</button>' +
                '<button class="btn btn-outline-secondary btn-sm" id="oCCRetryVoice">' +
                '<i class="fa fa-refresh me-1"></i> Re-record</button>' +
                '</div></div>'
            );

            const sendVoiceBtn = document.getElementById('oCCSendVoice');
            if (sendVoiceBtn) {
                sendVoiceBtn.addEventListener('click', () => {
                    this.switchTab('chat');
                    this.sendMessage('[Voice message: User sent a recorded voice enquiry. Please process and assist with their insurance needs.]');
                    this.setTranscript('');
                    this.setRecordUI(false);
                });
            }
            const retryBtn = document.getElementById('oCCRetryVoice');
            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    this.setTranscript('');
                    this.setRecordUI(false);
                });
            }
        },

        setTranscript(html) {
            const el = document.getElementById('oCCTranscript');
            if (el) el.innerHTML = html;
        },

        startWaveAnimation() {
            document.querySelectorAll('.o_cc_wave_bar').forEach((bar, i) => {
                bar._waveInterval = setInterval(() => {
                    const h = 6 + Math.random() * 38;
                    bar.style.height = h + 'px';
                }, 100 + i * 25);
            });
        },

        stopWaveAnimation() {
            document.querySelectorAll('.o_cc_wave_bar').forEach(bar => {
                if (bar._waveInterval) clearInterval(bar._waveInterval);
                bar.style.height = '6px';
            });
        },

        // ── FILE UPLOAD ─────────────────────────────────────────────────
        handleFiles(fileList) {
            Array.from(fileList).forEach(file => {
                if (file.size > 15 * 1024 * 1024) {
                    alert('File "' + file.name + '" exceeds the 15 MB limit.');
                    return;
                }
                this.uploadedFiles.push(file);
            });
            this.renderFileList();
        },

        renderFileList() {
            const list = document.getElementById('oCCFileList');
            if (!list) return;

            const extIcons = {
                pdf: 'fa-file-pdf-o text-danger',
                doc: 'fa-file-word-o text-primary', docx: 'fa-file-word-o text-primary',
                xls: 'fa-file-excel-o text-success', xlsx: 'fa-file-excel-o text-success',
                jpg: 'fa-file-image-o text-warning', jpeg: 'fa-file-image-o text-warning',
                png: 'fa-file-image-o text-warning', gif: 'fa-file-image-o text-warning',
                zip: 'fa-file-zip-o text-secondary', rar: 'fa-file-zip-o text-secondary',
            };

            list.innerHTML = this.uploadedFiles.map((file, idx) => {
                const ext = (file.name.split('.').pop() || '').toLowerCase();
                const icon = extIcons[ext] || 'fa-file-o text-secondary';
                const size = file.size < 1024 ? file.size + ' B'
                    : file.size < 1048576 ? (file.size / 1024).toFixed(1) + ' KB'
                    : (file.size / 1048576).toFixed(1) + ' MB';
                return (
                    '<div class="o_cc_file_item">' +
                    '<i class="fa ' + icon + ' o_cc_file_icon"></i>' +
                    '<div class="o_cc_file_info">' +
                    '<div class="o_cc_file_name">' + this.escHtml(file.name) + '</div>' +
                    '<div class="o_cc_file_size">' + size + '</div>' +
                    '</div>' +
                    '<button class="o_cc_file_remove" data-remove="' + idx + '" title="Remove">' +
                    '<i class="fa fa-times"></i></button>' +
                    '</div>'
                );
            }).join('');

            list.querySelectorAll('[data-remove]').forEach(btn => {
                btn.addEventListener('click', e => {
                    e.stopPropagation();
                    this.uploadedFiles.splice(parseInt(btn.dataset.remove), 1);
                    this.renderFileList();
                });
            });

            const sendFilesBtn = document.getElementById('oCCSendFiles');
            if (sendFilesBtn) {
                sendFilesBtn.style.display = this.uploadedFiles.length > 0 ? 'block' : 'none';
            }
        },

        sendFilesAsMessage() {
            const names = this.uploadedFiles.map(f => f.name).join(', ');
            this.switchTab('chat');
            this.sendMessage('[Documents uploaded: ' + names + ' — Please process these documents for my insurance application.]');
            this.uploadedFiles = [];
            this.renderFileList();
        },

        escHtml(str) {
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        },
    };

    // ── BOOT ──────────────────────────────────────────────────────────
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => CC.init());
    } else {
        CC.init();
    }

    window.AmeenCallCenter = CC;

})();
