import hashlib
import hmac
import json

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestSnailmailWebhook(HttpCase):
    """
    Test the snailmail webhook controller.

    Flow being tested:
        IAP server  →  POST /webhook/snailmail/1/<event_type>  →  User DB
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Partner who will receive the letter
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'street': 'Test Street 1',
            'zip': '1234',
            'city': 'Test City',
            'country_id': cls.env.ref('base.ch').id,
        })

        # Invoice linked to the letter
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'invoice_date': '2024-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'Test product',
                'price_unit': 100.0,
                'quantity': 1,
            })],
        })
        cls.invoice.action_post()

        # The pingen letter document_id — simulates what Pingen assigns
        cls.pingen_letter_id = 'test-pingen-letter-uuid-1234'

        # Create the snailmail letter linked to the invoice
        cls.letter = cls.env['snailmail.letter'].create({
            'partner_id': cls.partner.id,
            'model': 'account.move',
            'res_id': cls.invoice.id,
            'user_id': cls.env.user.id,
            'company_id': cls.invoice.company_id.id,
            'document_id': cls.pingen_letter_id,
            'state': 'pending',
        })

        # The IAP account token used for signing
        iap_service = cls.env.ref('snailmail.iap_service_snailmail')
        cls.iap_account = cls.env['iap.account'].create({
            'name': 'snailmail',
            'account_token': 'test_iap_account_token_1234',
            'service_id': iap_service.id,
        })
        cls.account_token = cls.iap_account.account_token
        cls.hashed_token = hashlib.sha1(
            cls.account_token.encode('utf-8')
        ).hexdigest()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _make_payload(self, letter_id=None, status=None, reason=None):
        """Build the event payload IAP sends"""
        payload = {
            'letter_id': letter_id or self.pingen_letter_id,
            'status': status or 'delivered',
        }
        if reason:
            payload['reason'] = reason
        return payload

    def _make_signature(self, payload, token=None):
        """Generate HMAC signature the way IAP does."""
        sign_token = token or self.hashed_token
        return hmac.new(
            key=sign_token.encode(),
            msg=json.dumps(payload, sort_keys=True).encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def _post_webhook(self, event_type, payload, signature=None):
        """Send a POST request to the webhook endpoint."""
        body = json.dumps(payload, sort_keys=True).encode()
        sig = signature or self._make_signature(payload)
        return self.url_open(
            f'/webhook/snailmail/1/{event_type}',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'odoo-iap-signature': sig,
            },
        )

    # -------------------------------------------------------------------------
    # Valid cases
    # -------------------------------------------------------------------------

    def test_webhook_delivered(self):
        """Valid 'delivered' webhook updates letter state and posts chatter message."""
        payload = self._make_payload(status='delivered')
        response = self._post_webhook('delivered', payload)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'accepted', response.content)
        self.letter._invalidate_cache()
        self.assertEqual(self.letter.state, 'delivered')

        # Chatter message posted on the invoice
        message = self.env['mail.message'].search([
            ('res_id', '=', self.invoice.id),
            ('model', '=', 'account.move'),
        ], order='id desc', limit=1)
        self.assertTrue(message)
        self.assertIn('delivered', message.body)

    def test_webhook_undeliverable(self):
        """Valid 'undeliverable' webhook updates letter state, error_code"""
        payload = self._make_payload(
            status='undeliverable',
            reason='Recipient moved to a new address'
        )
        response = self._post_webhook('undeliverable', payload)
        self.assertEqual(response.status_code, 200)
        self.letter._invalidate_cache()
        self.assertEqual(self.letter.state, 'undeliverable')
        self.assertEqual(self.letter.error_code, 'LETTER_UNDELIVERABLE')
        self.assertEqual(self.letter.info_msg.striptags(), 'Recipient moved to a new address')

    # -------------------------------------------------------------------------
    # Invalid cases
    # -------------------------------------------------------------------------

    def test_webhook_invalid_event_type(self):
        """Unknown event_type returns 404."""
        payload = self._make_payload(status='delivered')
        response = self._post_webhook('unknown_event', payload)
        self.assertEqual(response.status_code, 404)

    def test_webhook_invalid_signature(self):
        """Wrong signature returns 404."""
        payload = self._make_payload(status='delivered')
        response = self._post_webhook(
            'delivered',
            payload,
            signature='a' * 64,   # wrong but valid-length hex string
        )
        self.assertEqual(response.status_code, 404)

    def test_webhook_missing_letter_id(self):
        """Missing letter_id in payload returns 404."""
        payload = {'status': 'delivered'}   # no letter_id
        response = self._post_webhook('delivered', payload)
        self.assertEqual(response.status_code, 404)

    def test_webhook_missing_status(self):
        """Missing status in payload returns 404."""
        payload = {'letter_id': self.pingen_letter_id}   # no status
        response = self._post_webhook('delivered', payload)
        self.assertEqual(response.status_code, 404)

    def test_webhook_letter_not_found(self):
        """Unknown pingen_letter_id returns 404."""
        payload = self._make_payload(letter_id='non-existent-uuid')
        response = self._post_webhook('delivered', payload)
        self.assertEqual(response.status_code, 404)

    def test_webhook_empty_payload(self):
        """Empty payload returns 404."""
        response = self._post_webhook('delivered', {})
        self.assertEqual(response.status_code, 404)
