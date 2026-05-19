from odoo import models, fields, api


class InsuranceClaim(models.Model):
    _name = 'insurance.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'claim_number'
    _order = 'incident_date desc'

    claim_number = fields.Char(
        string='Claim Number', required=True, copy=False,
        readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('insurance.claim')
    )
    policy_id = fields.Many2one('insurance.policy', string='Policy', required=True, tracking=True, ondelete='restrict')
    client_id = fields.Many2one('insurance.client', string='Client', related='policy_id.client_id', store=True, readonly=True)
    insurance_type = fields.Selection(related='policy_id.insurance_type', store=True, readonly=True, string='Insurance Type')
    insurer = fields.Char(related='policy_id.insurer', store=True, readonly=True, string='Insurer')

    status = fields.Selection([
        ('reported', 'Reported'),
        ('documents_collected', 'Documents Collected'),
        ('submitted', 'Submitted to Insurer'),
        ('under_assessment', 'Under Assessment'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('settled', 'Settled'),
    ], string='Status', default='reported', tracking=True)

    incident_date = fields.Date(string='Incident Date', required=True)
    reported_date = fields.Date(string='Reported Date', default=fields.Date.today)
    claim_amount = fields.Float(string='Claim Amount', required=True, tracking=True)
    settled_amount = fields.Float(string='Settled Amount', tracking=True)
    description = fields.Text(string='Incident Description')
    surveyor_notes = fields.Text(string='Surveyor Notes')
    rejection_reason = fields.Text(string='Rejection Reason')
    settlement_date = fields.Date(string='Settlement Date')

    document_ids = fields.Many2many(
        'ir.attachment', string='Supporting Documents',
        help='Upload claim documents: photos, police reports, medical records, etc.'
    )

    def action_collect_documents(self):
        self.write({'status': 'documents_collected'})

    def action_submit_to_insurer(self):
        self.write({'status': 'submitted'})
        self.message_post(
            body=f'Claim {self.claim_number} submitted to {self.insurer} on {fields.Date.today()}.',
            message_type='notification',
        )

    def action_mark_under_assessment(self):
        self.write({'status': 'under_assessment'})

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_settle(self):
        self.ensure_one()
        self.write({'status': 'settled', 'settlement_date': fields.Date.today()})
        if not self.settled_amount:
            self.settled_amount = self.claim_amount
