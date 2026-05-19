/* ═══════════════════════════════════════════════════════════════
   SAHAB AI Chat Widget — Ultimate Combined Version (2026)
   Maintains full conversation history, immediate Odoo contextual 
   intelligence, Base64 document attachment, and live voice-to-text.
   ═══════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    const SAHAB = {
        panel: null,
        trigger: null,
        messagesEl: null,
        inputEl: null,
        contextInput: null,
        isOpen: false,
        sessionId: null,
        history: [],          // Full conversation history [{role, content}]
        applicationCreated: false,
        
        // المرفق الحالي النشط قيد الإرسال
        currentAttachment: {
            base64: null,
            filename: null,
            mimeType: null
        },

        // متغيرات معالجة الصوت وتحويله إلى نصوص
        recognition: null,
        isListening: false,

        init() {
            this.sessionId = 'sahab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            this.panel      = document.getElementById('oSahabPanel');
            this.trigger    = document.getElementById('oSahabTrigger');
            this.messagesEl = document.getElementById('oSahabMessages');
            this.inputEl    = document.getElementById('oSahabInput');
            this.contextInput = document.getElementById('oSahabClientContext');
            
            if (!this.panel || !this.trigger) return;
            
            this._initVoiceRecognition();
            this._bindEvents();
        },

        _bindEvents() {
            // حدث النقر لفتح وإغلاق المساعد الذكي
            this.trigger.addEventListener('click', () => this.toggle());
            
            const closeBtn = document.getElementById('oSahabClose');
            if (closeBtn) closeBtn.addEventListener('click', () => this.close());

            const sendBtn = document.getElementById('oSahabSend');
            if (sendBtn) sendBtn.addEventListener('click', () => this._sendUserInput());

            // ── دمج معالجة حقل النص المطور (Gemini Style) ──
            if (this.inputEl) {
                // تمدد الحقل مرناً مع الأسطر والكتابة
                this.inputEl.addEventListener('input', function () {
                    this.style.height = 'auto';
                    this.style.height = this.scrollHeight + 'px';
                });

                this.inputEl.addEventListener('keydown', e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        this._sendUserInput();
                        // تصفير الطول والارتفاع تلقائياً بعد الإرسال ليتحول لسطر واحد
                        this.inputEl.style.height = 'auto';
                    }
                });
            }

            // ربط أحداث معالجة الملفات والمستندات
            const attachBtn = document.getElementById('oSahabAttachFile');
            const fileInput = document.getElementById('oSahabFileInput');
            if (attachBtn && fileInput) {
                attachBtn.addEventListener('click', () => fileInput.click());
                fileInput.addEventListener('change', (e) => this._handleFileSelection(e));
            }

            // ربط الكاميرا والتقاط صور الحوادث
            const cameraBtn = document.getElementById('oSahabCameraCapture');
            const cameraInput = document.getElementById('oSahabCameraInput');
            if (cameraBtn && cameraInput) {
                cameraBtn.addEventListener('click', () => cameraInput.click());
                cameraInput.addEventListener('change', (e) => this._handleFileSelection(e));
            }

            // ربط ميكروفون تحويل الصوت لنصوص
            const voiceBtn = document.getElementById('oSahabVoiceRecord');
            if (voiceBtn) {
                voiceBtn.addEventListener('click', () => this._toggleVoiceListening());
            }

            // زر حذف المرفق قبل الإرسال
            const removeAttachBtn = document.getElementById('oRemoveAttachment');
            if (removeAttachBtn) {
                removeAttachBtn.addEventListener('click', () => this._clearAttachmentPreview());
            }
        },

        async toggle() { 
            if (this.isOpen) {
                this.close();
            } else {
                // استباقياً وعاجلاً: بمجرد النقر، نحدث عقل الإيجنت ببيانات وسجل تتبع العميل من أودو
                await this._updateAgentBrainContext();
                this.open();
            }
        },

        open() {
            this.isOpen = true;
            this.panel.classList.add('open');
            const badge = this.trigger.querySelector('.o_sahab_badge');
            if (badge) badge.style.display = 'none';
            if (this.history.length === 0) this._startConversation();
        },

        close() {
            this.isOpen = false;
            this.panel.classList.remove('open');
            if (this.isListening) this._stopVoiceListening();
        },

        // تحديث عقل الأيجنت عبر الـ RPC ببيانات العميل الحية لتكون جاهزة قبل الترحيب
        async _updateAgentBrainContext() {
            try {
                const clientContextData = await this._rpc('/sahab/ai/fetch_client_dashboard_context', {});
                if (this.contextInput && clientContextData) {
                    this.contextInput.value = JSON.stringify(clientContextData);
                    console.log("✅ SAHAB Brain Updated with Odoo Client Portfolio Data.");
                }
            } catch (e) {
                console.error("❌ Failed to populate real-time agent profile brain context:", e);
            }
        },

        // إعداد مفسر ومترجم الصوت الذكي المتوافق مع المتصفحات والهواتف الذكية
        _initVoiceRecognition() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                const voiceBtn = document.getElementById('oSahabVoiceRecord');
                if (voiceBtn) voiceBtn.style.display = 'none';
                return;
            }
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.lang = 'ar-OM'; // اللهجة العمانية/العربية المعتمدة بالسلطنة
            this.recognition.interimResults = false;

            this.recognition.onstart = () => {
                this.isListening = true;
                const voiceBtn = document.getElementById('oSahabVoiceRecord');
                if (voiceBtn) {
                    voiceBtn.style.color = '#ef4444';
                    voiceBtn.style.transform = 'scale(1.2)';
                }
                if (this.inputEl) this.inputEl.placeholder = 'جاري الاستماع لصوتك وترجمته لنص...';
            };

            this.recognition.onresult = (event) => {
                const speechToTextResult = event.results[0][0].transcript;
                if (this.inputEl && speechToTextResult) {
                    this.inputEl.value = (this.inputEl.value + ' ' + speechToTextResult).trim();
                    // تفعيل التمدد التلقائي بعد إدخال النص الصوتي المترجم مباشرة
                    this.inputEl.dispatchEvent(new Event('input'));
                }
            };

            this.recognition.onerror = (e) => {
                console.error("Voice Recognition Error:", e);
                this._stopVoiceListening();
            };

            this.recognition.onend = () => {
                this._stopVoiceListening();
            };
        },

        _toggleVoiceListening() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                alert("تسجيل الصوت غير مدعوم على هذا المتصفح أو يتطلب اتصال أمان HTTPS.");
                return;
            }
            if (!this.recognition) return;
            this.isListening ? this._stopVoiceListening() : this.recognition.start();
        },

        _stopVoiceListening() {
            this.isListening = false;
            const voiceBtn = document.getElementById('oSahabVoiceRecord');
            if (voiceBtn) {
                voiceBtn.style.color = '#6b7280';
                voiceBtn.style.transform = 'scale(1)';
            }
            if (this.inputEl) this.inputEl.placeholder = 'اكتب رسالتك هنا أو استخدم الصوت والمرفقات…';
            if (this.recognition) this.recognition.stop();
        },

        // معالجة الملفات المرفقة وتشفيرها فورياً في المتصفح إلى Base64
        _handleFileSelection(event) {
            const file = event.target.files[0];
            if (!file) return;

            // تحديد حد أقصى لحجم المرفق (5 ميجابايت لحماية شبكة الويب هوك)
            if (file.size > 5 * 1024 * 1024) {
                alert("حجم الملف كبير جداً، يرجى إرفاق مستند أو صورة أقل من 5 ميجابايت.");
                return;
            }

            const reader = new FileReader();
            reader.onload = () => {
                this.currentAttachment.base64 = reader.result.split(',')[1];
                this.currentAttachment.filename = file.name;
                this.currentAttachment.mimeType = file.type;

                // إظهار المرفق في المعاينة المرئية للواجهة الأمامية
                const previewRow = document.getElementById('oSahabAttachmentPreview');
                const filenameLabel = previewRow ? previewRow.querySelector('.o_preview_filename') : null;
                if (previewRow && filenameLabel) {
                    filenameLabel.textContent = `📎 قيد الإرسال: ${file.name}`;
                    previewRow.style.display = 'flex';
                }
            };
            reader.readAsDataURL(file);
        },

        _clearAttachmentPreview() {
            this.currentAttachment.base64 = null;
            this.currentAttachment.filename = null;
            this.currentAttachment.mimeType = null;
            const previewRow = document.getElementById('oSahabAttachmentPreview');
            if (previewRow) previewRow.style.display = 'none';
            
            const fileInput = document.getElementById('oSahabFileInput');
            if (fileInput) fileInput.value = '';
            
            const cameraInput = document.getElementById('oSahabCameraInput');
            if (cameraInput) cameraInput.value = '';
        },

        // ── Fetch welcome message then start real AI conversation ──────────
        async _startConversation() {
            this._showTyping();
            try {
                const ctx = await this._rpc('/sahab/ai/context', {});
                this._hideTyping();

                const welcome = ctx.welcome_message || 'أهلاً! أنا SAHAB AI، كيف أقدر أساعدك؟';
                this._renderAgentMessage(welcome, []);

                // إضافة الترحيب للسجل للحفاظ على السياق
                this.history.push({ role: 'assistant', content: welcome });

            } catch (e) {
                this._hideTyping();
                const fallback = 'أهلاً وسهلاً! أنا صحاب، مساعدك الذكي للتأمين. كيف أقدر أساعدك؟';
                this._renderAgentMessage(fallback, []);
                this.history.push({ role: 'assistant', content: fallback });
            }
        },

        // ── User sends a message ───────────────────────────────────────────
        async _sendUserInput() {
            if (!this.inputEl) return;
            const msg = this.inputEl.value.trim();
            const hasFile = this.currentAttachment.base64 !== null;

            if (!msg && !hasFile) return; // منع الإرسال الفارغ
            if (this.applicationCreated) return;

            this.inputEl.value = '';
            // تصفير طول الحقل فورياً بعد الإرسال وتطهير مساحته برمجياً
            this.inputEl.style.height = 'auto';
            
            // صياغة وعرض الرسالة بشكل منسق في الواجهة للمستخدم
            let displayMsg = msg;
            if (hasFile) {
                displayMsg = msg ? `📎 [ملف: ${this.currentAttachment.filename}] \n ${msg}` : `📎 [ملف: ${this.currentAttachment.filename}]`;
            }
            
            this._renderUserMessage(displayMsg);
            this.history.push({ role: 'user', content: displayMsg });

            // استخراج سياق العميل المخفي المجلوب من أودو لإرساله كاملاً للـ Webhook
            let parsedContext = {};
            if (this.contextInput && this.contextInput.value) {
                try { parsedContext = JSON.parse(this.contextInput.value); } catch(e){}
            }

            // الحزمة المتقدمة الشاملة للمحادثة، المرفقات بصيغة Base64، وسياق قواعد البيانات
            const payloadToSend = {
                message: msg,
                session_id: this.sessionId,
                history: this.history.slice(0, -1),
                context: parsedContext,
                attachment: hasFile ? {
                    base64: this.currentAttachment.base64,
                    filename: this.currentAttachment.filename,
                    mime_type: this.currentAttachment.mimeType
                } : null
            };

            this._clearAttachmentPreview();
            await this._callAIWithPayload(payloadToSend);
        },

        // ── Option button clicked ──────────────────────────────────────────
        async _optionClicked(value, label, action, btn) {
            const row = btn.closest('.o_sahab_options');
            if (row) row.querySelectorAll('.o_sahab_option_btn').forEach(b => {
                b.disabled = true;
                b.classList.remove('selected');
            });
            btn.classList.add('selected');

            if (action === 'open_url') {
                setTimeout(() => { window.location.href = value; }, 800);
                return;
            }

            this._renderUserMessage(label);
            this.history.push({ role: 'user', content: label });

            let parsedContext = {};
            if (this.contextInput && this.contextInput.value) {
                try { parsedContext = JSON.parse(this.contextInput.value); } catch(e){}
            }

            const payloadToSend = {
                message: label,
                session_id: this.sessionId,
                history: this.history.slice(0, -1),
                context: parsedContext,
                attachment: null
            };

            await this._callAIWithPayload(payloadToSend);
        },

        // ── Core: call AI with full Payload ────────────────────────────────
        async _callAIWithPayload(payload) {
            this._setInputEnabled(false);
            this._showTyping();

            try {
                const data = await this._rpc('/sahab/ai/chat', payload);
                this._hideTyping();

                const reply   = data.reply   || '';
                const options = data.options  || [];

                if (reply) {
                    this._renderAgentMessage(reply, options);
                    this.history.push({ role: 'assistant', content: reply });
                }

                if (data.application_created) {
                    this.applicationCreated = true;
                    this._setInputEnabled(false);
                    if (data.portal_url) this._showPortalButton(data.portal_url);
                } else {
                    this._setInputEnabled(true);
                }

            } catch (e) {
                this._hideTyping();
                const errMsg = 'عذراً، حدث خطأ مؤقت في خادم سحاب. يرجى المحاولة مجدداً.';
                this._renderAgentMessage(errMsg, []);
                this.history.push({ role: 'assistant', content: errMsg });
                this._setInputEnabled(true);
            }
        },

        // ── Render helpers ─────────────────────────────────────────────────
        _renderAgentMessage(text, options) {
            const wrapper = document.createElement('div');
            wrapper.className = 'o_sahab_msg agent';

            const avatar = document.createElement('div');
            avatar.className = 'o_sahab_msg_avatar';
            avatar.innerHTML = '<i class="fa fa-robot"></i>';

            const contentCol = document.createElement('div');
            contentCol.style.flex = '1';
            contentCol.style.minWidth = '0';

            const bubble = document.createElement('div');
            bubble.className = 'o_sahab_bubble';
            bubble.textContent = text;
            contentCol.appendChild(bubble);

            if (options && options.length) {
                const optRow = document.createElement('div');
                optRow.className = 'o_sahab_options';
                options.forEach(opt => {
                    const btn = document.createElement('button');
                    btn.className = 'o_sahab_option_btn';
                    
                    btn.textContent = typeof opt === 'string' ? opt : (opt.label || opt.value);
                    const val    = typeof opt === 'string' ? opt : (opt.value || opt.label);
                    const act    = typeof opt === 'string' ? 'select' : (opt.action || 'select');
                    const lbl    = typeof opt === 'string' ? opt : (opt.label || opt.value);
                    
                    btn.addEventListener('click', () => this._optionClicked(val, lbl, act, btn));
                    optRow.appendChild(btn);
                });
                contentCol.appendChild(optRow);
            }

            wrapper.appendChild(avatar);
            wrapper.appendChild(contentCol);
            this.messagesEl.appendChild(wrapper);
            this._scrollToBottom();
        },

        _renderUserMessage(text) {
            const wrapper = document.createElement('div');
            wrapper.className = 'o_sahab_msg user';
            
            const avatar = document.createElement('div');
            avatar.className = 'o_sahab_msg_avatar';
            avatar.innerHTML = '<i class="fa fa-user"></i>';
            
            const bubble = document.createElement('div');
            bubble.className = 'o_sahab_bubble';
            bubble.style.whiteSpace = 'pre-wrap'; 
            bubble.textContent = text;
            
            wrapper.appendChild(bubble);
            wrapper.appendChild(avatar);
            this.messagesEl.appendChild(wrapper);
            this._scrollToBottom();
        },

        _typingEl: null,
        _showTyping() {
            if (this._typingEl) return;
            const wrapper = document.createElement('div');
            wrapper.className = 'o_sahab_msg agent';
            const avatar = document.createElement('div');
            avatar.className = 'o_sahab_msg_avatar';
            avatar.innerHTML = '<i class="fa fa-robot"></i>';
            const typing = document.createElement('div');
            typing.className = 'o_sahab_typing';
            typing.innerHTML = '<span></span><span></span><span></span>';
            wrapper.appendChild(avatar);
            wrapper.appendChild(typing);
            this._typingEl = wrapper;
            this.messagesEl.appendChild(wrapper);
            this._scrollToBottom();
        },
        
        _hideTyping() {
            if (this._typingEl) { this._typingEl.remove(); this._typingEl = null; }
        },

        _showPortalButton(url) {
            const wrapper = document.createElement('div');
            wrapper.className = 'o_sahab_msg agent';
            const a = document.createElement('a');
            a.href = url;
            a.className = 'btn btn-primary btn-sm mt-2';
            a.innerHTML = '<i class="fa fa-external-link me-1"></i>فتح البوابة الإلكترونية';
            wrapper.appendChild(a);
            this.messagesEl.appendChild(wrapper);
            this._scrollToBottom();
        },

        _setInputEnabled(enabled) {
            if (this.inputEl) this.inputEl.disabled = !enabled;
            const sendBtn = document.getElementById('oSahabSend');
            if (sendBtn) sendBtn.disabled = !enabled;
        },

        _scrollToBottom() {
            if (this.messagesEl) this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        },

        async _rpc(url, params) {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params }),
            });
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const json = await resp.json();
            if (json.error) throw new Error(json.error.data?.message || json.error.message || 'RPC error');
            return json.result;
        },
    };

    // التشغيل المتوافق والآمن لمنع الشاشة السوداء في واجهات أودو
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        SAHAB.init();
    } else {
        window.addEventListener('load', () => SAHAB.init());
    }
    window.SAHAB = SAHAB;
})();
