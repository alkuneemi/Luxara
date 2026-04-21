# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account_payment_custom.tests.common import AccountPaymentCustomCommon


@tagged("-at_install", "post_install")
class TestPaymentProvider(AccountPaymentCustomCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wire_transfer_cron = cls.env.ref(
            "account_payment_custom.cron_auto_confirm_paid_wire_transfer_txs"
        )

    def test_wire_transfer_accounting_configuration(self):
        """Make sure the right `account.payment.method.line` is created."""
        self.assertIn(
            "wire_transfer", self.provider.journal_id.inbound_payment_method_line_ids.mapped("code")
        )

    def test_installing_provider_activates_processing_cron(self):
        """Test that the post-processing cron is activated when a provider is installed."""
        self.wire_transfer_cron.active = False  # Reset the cron's active field.
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider.search_count",
            return_value=1,
        ):
            self.provider._setup_provider("custom")
            self.assertTrue(self.wire_transfer_cron.active)

    def test_uninstalling_provider_deactivates_processing_cron(self):
        """Test that the post-processing cron is deactivated when a provider is disabled."""
        self.wire_transfer_cron.active = True
        self.provider._remove_provider("custom")
        self.assertFalse(self.wire_transfer_cron.active)
