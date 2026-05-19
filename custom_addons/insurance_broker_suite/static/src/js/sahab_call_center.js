/** @odoo-module **/

document.addEventListener("DOMContentLoaded", function () {
    const ccOverlay = document.getElementById("oCCOverlay");
    const ccRecordBtn = document.getElementById("oCCRecord");
    const ccVoiceStatus = document.getElementById("oCCVoiceStatus");
    const ccTranscript = document.getElementById("oCCTranscript");
    const micIcon = document.getElementById("micIcon");
    const ccWaveform = document.querySelector(".o_cc_waveform");
    
    if (!ccOverlay || !ccRecordBtn) return;

    let sessionId = localStorage.getItem("sahab_cc_session") || "";
    let isCallActive = false; 
    let currentAudio = null;
    let recognition = null;
    let silenceTimer = null;
    let finalTranscriptText = ""; // لتخزين النص النهائي المكتمل أثناء المكالمة
    const SILENCE_DURATION = 3000; 

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true; 
        recognition.interimResults = true; // تفعيل النتائج الفورية
        recognition.lang = 'ar-OM'; 

        recognition.onresult = function (event) {
            clearTimeout(silenceTimer); // إيقاف العداد بمجرد استمرار العميل في الحديث
            ccTranscript.style.display = "block";
            
            let interimTranscript = '';
            let currentFinal = '';

            // تجميع النص النهائي والمؤقت
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    currentFinal += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            finalTranscriptText += currentFinal;
            
            // دمج النص وعرضه (النص النهائي بالأسود، والنص الجاري استماعه بالرمادي)
            const fullTextForDisplay = finalTranscriptText + ' <span style="color: #64748b;">' + interimTranscript + '...</span>';
            const textToProcess = (finalTranscriptText + " " + interimTranscript).trim();

            ccTranscript.innerHTML = `
                <div class="mb-2">
                    <strong class="text-primary">🎙️ جاري الاستماع:</strong> 
                    <span class="text-dark fw-medium">${fullTextForDisplay}</span>
                </div>
            `;

            // إذا كان هناك نص فعلي، نبدأ عداد الصمت 3 ثوانٍ
            if (textToProcess.length > 0) {
                ccVoiceStatus.innerText = "🎙️ العميل يتحدث... (سيتم الرد تلقائياً فور صمتك)";
                silenceTimer = setTimeout(() => {
                    processAndSendSpeech(textToProcess);
                }, SILENCE_DURATION);
            }
        };

        recognition.onend = function () {
            // إعادة التشغيل التلقائي إذا توقف المحرك وكانت المكالمة لا تزال نشطة
            if (isCallActive && (!currentAudio || currentAudio.paused) && !silenceTimer) {
                try { recognition.start(); } catch(e) {}
            }
        };

        recognition.onerror = function (event) {
            console.error("Speech Recognition Error: ", event.error);
            if (event.error === 'no-speech' && isCallActive) {
                ccVoiceStatus.innerText = "نستمع إليك، تفضل بالتحدث...";
            }
        };
    }

    // إرسال النص إلى السيرفر
    function processAndSendSpeech(textToSend) {
        // إيقاف المايك لمنع التداخل
        try { recognition.stop(); } catch(e) {}
        
        if (textToSend) {
            finalTranscriptText = ""; // تصفير النص للمكالمة القادمة
            sendTextMessageToAI(textToSend);
        } else {
            restartListening();
        }
    }

    async function sendTextMessageToAI(textMessage) {
        ccVoiceStatus.innerText = "⚡ جاري تحليل طلبك والرد...";
        toggleWaveformAnimation(false);

        const formData = new FormData();
        formData.append("message", textMessage);
        if (sessionId) formData.append("session_id", sessionId);

        try {
            const response = await fetch("/sahab/ai/cc_interact", {
                method: "POST",
                body: formData
            });
            
            if (!response.ok) throw new Error(`HTTP Error Status: ${response.status}`);
            
            const data = await response.json();
            
            if (data.session_id) {
                sessionId = data.session_id;
                localStorage.setItem("sahab_cc_session", sessionId);
            }

            ccTranscript.innerHTML = `
                <div class="mb-2" style="border-bottom: 1px dashed #e2e8f0; padding-bottom: 6px;">
                    <strong class="text-primary">🎙️ أنت:</strong> ${textMessage}
                </div>
                <div class="mt-2">
                    <strong class="text-success">🤖 المستشار:</strong> ${data.reply}
                </div>
            `;

            if (data.audio_base64) {
                if (currentAudio) currentAudio.pause();
                
                currentAudio = new Audio("data:audio/mp3;base64," + data.audio_base64);
                ccVoiceStatus.innerText = "📞 المستشار يتحدث الآن...";
                toggleWaveformAnimation(true);
                
                await currentAudio.play();
                
                // الاستماع تلقائياً بمجرد انتهاء المقطع الصوتي
                currentAudio.onended = () => {
                    restartListening();
                };
            } else {
                restartListening();
            }

        } catch (error) {
            console.error("Transmission Error: ", error);
            ccVoiceStatus.innerText = "❌ حدث خطأ في الاتصال، أعد المحاولة.";
            setTimeout(restartListening, 2000);
        }
    }

    function restartListening() {
        if (!isCallActive) return;
        ccVoiceStatus.innerText = "🎙️ الخط مفتوح... تفضل بالتحدث";
        toggleWaveformAnimation(true);
        finalTranscriptText = ""; // تصفير النص
        ccTranscript.innerHTML = `<div class="text-muted">...</div>`;
        try { recognition.start(); } catch(e) {}
    }

    function toggleWaveformAnimation(active) {
        if (!ccWaveform) return;
        ccWaveform.style.opacity = active ? "1" : "0.2";
        const bars = ccWaveform.querySelectorAll(".o_cc_wave_bar");
        bars.forEach((bar, index) => {
            bar.style.animation = active ? `bounce 0.5s ease-in-out infinite alternate` : "none";
            if (active) bar.style.animationDelay = `${index * 0.08}s`;
        });
    }

    ccRecordBtn.addEventListener("click", function () {
        if (!recognition) {
            alert("ميزة التعرف على الصوت غير مدعومة في متصفحك. يرجى استخدام Google Chrome.");
            return;
        }

        if (isCallActive) {
            // إنهاء المكالمة
            isCallActive = false;
            clearTimeout(silenceTimer);
            try { recognition.stop(); } catch(e) {}
            if (currentAudio) currentAudio.pause();
            
            ccRecordBtn.style.background = "linear-gradient(135deg, #2563eb, #1d4ed8)";
            if (micIcon) micIcon.className = "fa fa-phone"; 
            ccVoiceStatus.innerText = "تم إنهاء المكالمة. اضغط للاتصال مجدداً.";
            toggleWaveformAnimation(false);
        } else {
            // بدء المكالمة
            isCallActive = true;
            finalTranscriptText = ""; 
            if (currentAudio) currentAudio.pause();
            
            ccRecordBtn.style.background = "linear-gradient(135deg, #ef4444, #dc2626)";
            if (micIcon) micIcon.className = "fa fa-stop"; 
            ccVoiceStatus.innerText = "📞 جاري الاتصال بالمستشار الذكي...";
            ccTranscript.style.display = "block";
            
            restartListening();
        }
    });
});
