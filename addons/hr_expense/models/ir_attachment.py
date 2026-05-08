from odoo import api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_from_submitted_expense(self):
        for attachment in self:
            if attachment.res_model != 'hr.expense' or not attachment.res_id:
                continue

            expense = self.env[attachment.res_model].browse(attachment.res_id)
            if not expense.has_access('write'):
                raise UserError(self.env._("You can't delete attachments from a submitted expense."))
