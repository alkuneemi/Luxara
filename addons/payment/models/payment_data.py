# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models
from odoo.fields import Domain

MAX_FAILURE_COUNT = 5  # The maximum number of processing attempts before giving up

_logger = logging.getLogger(__name__)


class PaymentData(models.Model):
    _name = "payment.data"
    _description = "Pending payment data payload to process"

    transaction_id = fields.Many2one(
        string="Transaction",
        comodel_name="payment.transaction",
        ondelete="restrict",
        required=True,
        index=True,
    )
    payload = fields.Json(string="Payload", required=True)
    failure_count = fields.Integer(string="Failure Count")

    @api.model
    def _cron_process(self):
        """Run the processing of pending payment data.

        Payment data records are processed in insertion order to ensure that older transactions are
        handled first and that same-transaction operations are applied in the correct sequence.

        After successful processing, payment data records are deleted. If it fails, they are kept
        for retry on the next run. Records that have reached the maximum failure count are left for
        manual intervention.

        :rtype: None
        """
        # Keep fetching pending payment data until all remaining records have been processed
        IrCron = self.env["ir.cron"]
        pending_payment_data_domain = Domain("failure_count", "<", MAX_FAILURE_COUNT)
        while pending_payment_data := self.env["payment.data"].search(pending_payment_data_domain):
            # Update the remaining count after each fetch to keep the cron running
            IrCron._commit_progress(remaining=len(pending_payment_data))

            for payment_data in pending_payment_data:
                # Lock the current records to prevent concurrent processing and restrict prefetching
                tx = payment_data.transaction_id.try_lock_for_update()
                payment_data = payment_data.try_lock_for_update()
                if not tx or not payment_data:  # The lock could not be acquired
                    IrCron._rollback_progress()  # Release the lock on whichever record was locked
                    continue  # Skip for now; will be retried on the next run

                try:
                    # Process the payment data
                    tx.with_context(payment_trusted_write=True)._process(payment_data.payload)
                    payment_data.unlink()
                except Exception:
                    IrCron._rollback_progress()
                    payment_data.failure_count += 1
                    _logger.exception(
                        "Failed to process payment data %s for transaction %s (attempt %s/%s).",
                        payment_data.id,
                        tx.reference,
                        payment_data.failure_count,
                        MAX_FAILURE_COUNT,
                    )

                # Commit the progress and check if we should stop
                remaining_time = IrCron._commit_progress(processed=1)
                if not remaining_time:
                    return
