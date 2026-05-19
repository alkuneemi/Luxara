/** @odoo-module */

import { jsonrpc } from "@web/core/network/rpc_service";

document.addEventListener("DOMContentLoaded", function () {
    const bubble = document.getElementById("omanAgentBubble");
    const titleEl = document.getElementById("omanAgentBubbleTitle");
    const textEl = document.getElementById("omanAgentBubbleText");
    const linkEl = document.getElementById("omanAgentBubbleLink");
    const closeBtn = document.getElementById("omanAgentBubbleClose");
    const testBtn = document.getElementById("testWebhookBtn");

    if (!bubble) return;

    // إغلاق يدوي
    closeBtn.addEventListener("click", () => {
        bubble.style.display = "none";
    });

    // دالة الاستعلام (يتم استدعاؤها عند ضغط زر التجربة)
    function testOmanAgentWebhook() {
        const currentPageUrl = window.location.pathname;
        const pageTitle = document.title || "تصفح التأمين";

        // تحديث النص للمستخدم ليعرف أن الطلب قيد التنفيذ
        titleEl.innerText = "جاري الاتصال...";
        textEl.innerText = "يتم الآن إرسال الويبهوك إلى n8n، يرجى الانتظار (ثانيتين)...";
        linkEl.classList.add("d-none");

        jsonrpc("/oman_agent/analyze_visit", {
            page_url: currentPageUrl,
            action_name: pageTitle
        }).then(function (data) {
            console.log("استجابة n8n:", data); // سيطبع الاستجابة في كونسول المتصفح (F12) لمساعدتك في التتبع

            if (data) {
                // سنقوم بعرض رسالة الترحيب كأولوية في وضع التجربة، أو التنبيه إذا لم يوجد ترحيب
                if (data.welcome) {
                    titleEl.innerText = "ترحيب / تشجيع 🌟";
                    textEl.innerHTML = data.welcome;
                } else if (data.alert) {
                    titleEl.innerText = "تنبيه هام 🔔";
                    textEl.innerHTML = data.alert;
                } else if (data.recommendation) {
                    titleEl.innerText = "نصيحة مستشارك 💡";
                    textEl.innerHTML = data.recommendation;
                } else {
                    titleEl.innerText = "استجابة افتراضية";
                    textEl.innerHTML = "تم الاتصال بنجاح ولكن لم يتم إرجاع نصوص من n8n.";
                }

                // عرض الإعلان إن وجد
                if (data.promo_ad && data.promo_ad.title) {
                    linkEl.setAttribute("href", data.promo_ad.link || "#");
                    linkEl.querySelector("span").innerText = data.promo_ad.title;
                    linkEl.classList.remove("d-none");
                }
            }
        }).catch(function (error) {
            console.error("خطأ في الاتصال:", error);
            titleEl.innerText = "خطأ ❌";
            textEl.innerText = "حدث خطأ أثناء الاتصال بالخادم، راجع الـ Console.";
        });
    }

    // ربط الزر بالدالة
    if (testBtn) {
        testBtn.addEventListener("click", function(e) {
            e.preventDefault();
            testOmanAgentWebhook();
        });
    }
});
