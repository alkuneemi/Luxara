import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";

async function paypalOnboardingAction(env, action) {
    const paypalUrl = action.params.paypal_url;
    const targetUrl = `/payment/paypal/oauth/return?csrf_token=${odoo.csrf_token}`;

    window.onboardedCallback = function(authCode, sharedId) {
        fetch(targetUrl, {
            method: 'POST',
            headers: {
                'content-type': 'application/json'
            },
            body: JSON.stringify({
                authCode: authCode,
                sharedId: sharedId,
                providerId: action.params.provider_id
            })
        }).then(function(res) {
            if (res.ok) {
                window.location.reload();
            } else {
                alert("Something went wrong with the PayPal onboarding integration.");
            }
        });
    };


    let hiddenBtn = document.getElementById('paypal-hidden-onboarding-btn');

    if (!hiddenBtn) {
        hiddenBtn = document.createElement('a');
        hiddenBtn.id = 'paypal-hidden-onboarding-btn';
        hiddenBtn.setAttribute('data-paypal-onboard-complete', 'onboardedCallback');
        hiddenBtn.setAttribute('data-paypal-button', 'true');
        hiddenBtn.style.display = 'none';
        document.body.appendChild(hiddenBtn);
    }

    hiddenBtn.href = paypalUrl + "&displayMode=minibrowser";

    await loadJS("https://www.sandbox.paypal.com/webapps/merchantboarding/js/lib/lightbox/partner.js");

    setTimeout(() => {
        hiddenBtn.click();
    }, 200);
}

registry.category("actions").add("paypal_onboarding_client_action", paypalOnboardingAction);
