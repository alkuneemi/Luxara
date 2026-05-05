# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class AccountMove(models.Model):

    _inherit = 'account.move'

    @api.depends('partner_id', 'line_ids.balance', 'journal_id')
    def _compute_l10n_es_is_simplified(self):
        for move in self:
            super()._compute_l10n_es_is_simplified()
            if move.journal_id.get_external_id().get(move.journal_id.id) == 'l10n_es_ecommerce.simplified_journal':
                move.l10n_es_is_simplified = True
