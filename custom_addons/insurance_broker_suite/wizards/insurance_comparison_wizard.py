from odoo import models, fields, api


class InsuranceComparisonWizard(models.TransientModel):
    _name = 'insurance.comparison.wizard'
    _description = 'Quote Comparison Wizard'

    rfq_id = fields.Many2one('insurance.rfq', string='RFQ', required=True)
    quote_ids = fields.Many2many(
        'insurance.rfq.quote', string='Quotes to Compare',
        compute='_compute_quotes', store=True, readonly=False,
    )
    recommended_id = fields.Many2one('insurance.rfq.quote', string='Recommended Quote')
    comparison_notes = fields.Html(string='AI Analysis &amp; Notes')

    @api.depends('rfq_id')
    def _compute_quotes(self):
        for rec in self:
            rec.quote_ids = rec.rfq_id.quote_ids if rec.rfq_id else []

    @api.onchange('rfq_id')
    def _onchange_rfq(self):
        if self.rfq_id and self.rfq_id.quote_ids:
            best = min(self.rfq_id.quote_ids, key=lambda q: q.premium)
            self.recommended_id = best
            self.comparison_notes = self._generate_ai_notes(best)

    def _generate_ai_notes(self, best_quote):
        quotes = self.rfq_id.quote_ids.sorted(key=lambda q: q.premium)
        lines = ['<p><strong>AI Underwriting Analysis</strong></p>', '<ul>']
        for q in quotes:
            marker = '[Recommended]' if q == best_quote else '-'
            lines.append(
                f'<li>{marker} <strong>{q.insurer}</strong>: Premium {q.premium:,.0f} OMR'
                f'{f", Deductible {q.deductible:,.0f} OMR" if q.deductible else ""}'
                f'{f", Settlement Ratio {q.claim_settlement_ratio}%" if q.claim_settlement_ratio else ""}'
                f'</li>'
            )
        lines.append('</ul>')
        lines.append(
            f'<p><strong>Recommendation:</strong> {best_quote.insurer} offers the best value '
            f'at {best_quote.premium:,.0f} OMR annual premium.</p>'
        )
        return '\n'.join(lines)

    def action_confirm_recommendation(self):
        self.ensure_one()
        if self.recommended_id:
            self.rfq_id.quote_ids.write({'is_recommended': False})
            self.recommended_id.write({'is_recommended': True})
            self.rfq_id.recommended_quote_id = self.recommended_id
        self.rfq_id.write({'status': 'comparison_ready'})
        return {'type': 'ir.actions.act_window_close'}
