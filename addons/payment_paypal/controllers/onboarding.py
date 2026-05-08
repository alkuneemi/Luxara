# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class PaypalOnboardingController(Controller):
    _oauth_return_url = "/payment/paypal/oauth/return"

    @route(_oauth_return_url, type="http", auth="user", methods=["POST"], website=True)
    def paypal_return_from_authorization(self):
        """Exchange the authorization code and shared id for an access token, retrieve seller
        credentials, and complete the PayPal onboarding process.
        This method is called via a JS fetch() request from the PayPal Integrated Sign-Up lightbox.

        :raise Validation Error: If an unexpected error occurs during API communication or when
                                writing the credentials to the database.
        :return: A JSON HTTP response indicating the success or failure of the onboarding flow.
                 On success, returns {'status': 'success'} to trigger a page reload on the client.
                 On failure, returns an error message and a 500 HTTP status code.
        :rtype: odoo.http.Response
        """
        data = json.loads(request.httprequest.data)
        _logger.info("Returning from authorization with data:\n%s", pprint.pformat(data))

        auth_code = data.get("authCode")
        shared_id = data.get("sharedId")
        provider_id = data.get("providerId")

        if not auth_code or not shared_id:
            raise ValidationError(
                _(
                    "Something went wrong with PayPal onboarding: Missing authCode, sharedId, or "
                    "session nonce."
                )
            )

        provider = request.env["payment.provider"].sudo().browse(provider_id)
        if not provider.exists():
            raise ValidationError(_("Could not find Paypal provider."))

        try:
            onboarding_token = provider._paypal_request_onboarding_token(auth_code, shared_id)
            response_content = provider._send_api_request(
                "GET",
                "/v1/customer/partners/QHZVTLZNWGSEW/merchant-integrations/credentials",
                onboarding_access_token=onboarding_token,
            )

            client_id = response_content["client_id"]
            client_secret = response_content["client_secret"]
            payer_id = response_content["payer_id"]

            provider.write({
                "paypal_client_id": client_id,
                "paypal_client_secret": client_secret,
                "paypal_account_id": payer_id,
            })
            provider._paypal_fetch_access_token()
            provider._paypal_check_onboarding_status()
            provider.action_paypal_create_webhook()

            return request.make_response(
                json.dumps({"status": "success"}), headers=[("Content-Type", "application/json")]
            )

        except ValidationError as e:
            _logger.error("PayPal Onboarding Error: %s", e)
            return request.make_response(
                json.dumps({"error": str(e)}),
                status=500,
                headers=[("Content-Type", "application/json")],
            )
