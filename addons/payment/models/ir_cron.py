# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import LockError


class IrCron(models.AbstractModel):
    _inherit = "ir.cron"

    @api.model
    def _run_payment_processing(self):
        processing_cron = self.env.ref("payment.process_payment_data_cron")
        try:
            processing_cron.lock_for_update(allow_referencing=True)  # Lock first to avoid UserError
        except LockError:  # The cron is already running
            return  # Nothing to do; wait for processing done notification
        processing_cron.sudo().method_direct_trigger()  # In sudo mode to run as superuser
