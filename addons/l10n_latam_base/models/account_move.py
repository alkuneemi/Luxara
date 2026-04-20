from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_record_vat_label(self, record):
        """ Extracts the VAT label from provided record"""
        if record and 'partner_id' in record._fields and record.partner_id.l10n_latam_identification_type_id:
            return record.partner_id.l10n_latam_identification_type_id.name
        return super().get_record_vat_label(record)
