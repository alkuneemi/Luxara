from odoo import models, fields, api


class InsuranceRfqQuote(models.Model):
    _name = 'insurance.rfq.quote'
    _description = 'Insurer Quote'
    _rec_name = 'insurer'
    _order = 'premium asc'

    rfq_id = fields.Many2one('insurance.rfq', string='RFQ', required=True, ondelete='cascade')
    insurer = fields.Char(string='Insurer', required=True)

    # Provider portal tracking
    provider_id = fields.Many2one(
        'insurance.company.provider', string='Provider Company',
        ondelete='set null', tracking=True,
    )
    submitted_via_portal = fields.Boolean(string='Submitted via Portal', default=False)
    submitted_at = fields.Datetime(string='Submitted At')
    premium = fields.Float(string='Annual Premium', required=True)
    deductible = fields.Float(string='Deductible')
    coverage = fields.Text(string='Coverage Details')
    exclusions = fields.Text(string='Exclusions')
    network = fields.Char(string='Network / TPA')
    add_ons = fields.Text(string='Add-ons / Benefits')
    claim_settlement_ratio = fields.Float(string='Claim Settlement Ratio (%)')
    validity_date = fields.Date(string='Quote Validity')
    is_recommended = fields.Boolean(string='Recommended', tracking=True)
    notes = fields.Text(string='Notes')
    score = fields.Float(string='AI Score', compute='_compute_score', store=True)

    @api.depends('premium', 'claim_settlement_ratio', 'deductible')
    def _compute_score(self):
        for rec in self:
            score = 100.0
            if rec.premium > 0:
                score -= (rec.premium / 10000) * 20
            if rec.claim_settlement_ratio > 0:
                score += (rec.claim_settlement_ratio / 100) * 30
            if rec.deductible > 0:
                score -= (rec.deductible / 5000) * 10
            rec.score = max(0.0, min(100.0, score))

    def action_mark_recommended(self):
        self.rfq_id.quote_ids.write({'is_recommended': False})
        self.write({'is_recommended': True})
        self.rfq_id.recommended_quote_id = self.id
