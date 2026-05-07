# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_id_ebupot_document = fields.Selection(selection=[
        ('Announcement', 'Announcement - Pengumuman'),
        ('CommercialInvoice', 'CommercialInvoice - Surat Tagihan'),
        ('Contract', 'Contract - Kontrak'),
        ('CurrentAccount', 'CurrentAccount - Jasa Giro'),
        ('Decree', 'Decree - Decree'),
        ('DeedOfEngagement', 'DeedOfEngagement - Akta Perjanjian'),
        ('DeedOfGeneral', 'DeedOfGeneral - Akta RUPS'),
        ('Other', 'Other - Lainnya'),
        ('OtherFacilityDoc', 'OtherFacilityDoc - Dokumen Fasilitas Lainnya'),
        ('PaymentProof', 'PaymentProof - Bukti Pembayaran'),
        ('StatementLetter', 'StatementLetter - Surat Pernyataan'),
        ('TaxInvoice', 'TaxInvoice - Faktur Pajak'),
        ('TaxRegulationDoc', 'TaxRegulationDoc - Dokumen Perpajakan'),
        ('TradeConfirmation', 'TradeConfirmation - Trade Confirmation')],
        default='CommercialInvoice',
        string="E-Bupot Document Type",
    )

    def _l10n_id_ebupot_build_invoice_vals(self, vals):
        self.ensure_one()
        vals.update({
            'Document': self.l10n_id_ebupot_document or 'CommercialInvoice',
            'DocumentNumber': self.ref,
            'DocumentDate': self.invoice_date.strftime("%Y-%m-%d"),
        })
