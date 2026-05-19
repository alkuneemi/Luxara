/** @odoo-module **/
/**
 * Insurance Website Funnel Tracker
 * - For logged-in users: tracks funnel steps via the /insurance/track JSON endpoint.
 * - For public users: the login modal is rendered server-side via show_login_modal=True.
 *   This script handles the modal's input focus and error display enhancements.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {

        // ── Auto-focus first input in the login modal ─────────────────────────
        var emailInput = document.getElementById('ins_email');
        if (emailInput) {
            setTimeout(function () { emailInput.focus(); }, 300);
        }

        // ── Show login error banner if redirected back with ?login_error=1 ─────
        if (window.location.search.indexOf('login_error=1') !== -1) {
            var errDiv = document.getElementById('ins_login_error');
            if (errDiv) {
                errDiv.classList.remove('d-none');
                errDiv.style.display = 'flex';
            }
        }

        // ── Async funnel step tracker for logged-in users ─────────────────────
        var overlay = document.getElementById('ins_login_overlay');
        if (overlay) {
            // User is not logged in — modal is showing, skip tracking
            return;
        }

        // Determine current page step
        var path = window.location.pathname;
        var step = null, actionName = '', catId = null, typeId = null, subtypeId = null;

        if (path === '/insurance' || path === '/insurance/') {
            step = '1_categories'; actionName = 'زار الأقسام الرئيسية';
        } else if (path.indexOf('/insurance/category/') !== -1 && path.indexOf('/types') !== -1) {
            step = '2_types'; actionName = 'زار الأنواع';
            var m = path.match(/\/insurance\/category\/(\d+)\/types/);
            if (m) catId = parseInt(m[1]);
        } else if (path.indexOf('/insurance/type/') !== -1 && path.indexOf('/subtypes') !== -1) {
            step = '3_subtypes'; actionName = 'زار الأنواع الفرعية';
            var m2 = path.match(/\/insurance\/type\/(\d+)\/subtypes/);
            if (m2) typeId = parseInt(m2[1]);
        } else if (path.indexOf('/insurance/application/form') !== -1) {
            step = '4_form'; actionName = 'فتح استمارة التقديم';
        } else if (path.indexOf('/insurance/payment') !== -1) {
            step = '5_payment'; actionName = 'وصل إلى صفحة الدفع';
        } else if (path.indexOf('/insurance/success') !== -1) {
            step = '6_completed'; actionName = 'أكمل العملية بنجاح';
        }

        // Fire and forget — server handles de-duplication
        if (step) {
            fetch('/insurance/track', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    jsonrpc: '2.0', method: 'call', id: 1,
                    params: {
                        step: step,
                        action_name: actionName,
                        page_url: path,
                        category_id: catId,
                        type_id: typeId,
                        subtype_id: subtypeId,
                    }
                })
            }).catch(function () { /* silent fail */ });
        }

    });

})();
