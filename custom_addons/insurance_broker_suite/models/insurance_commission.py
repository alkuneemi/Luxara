from odoo import models, fields, api
from datetime import date


class InsuranceCommission(models.Model):
    _name = 'insurance.commission'
    _description = 'Commission Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'due_date asc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    policy_id = fields.Many2one('insurance.policy', string='Policy', required=True, ondelete='restrict', tracking=True)
    client_id = fields.Many2one('insurance.client', related='policy_id.client_id', store=True, readonly=True, string='Client')
    insurer = fields.Char(related='policy_id.insurer', store=True, readonly=True, string='Insurer')
    insurance_type = fields.Selection(related='policy_id.insurance_type', store=True, readonly=True)

    expected_amount = fields.Float(string='Expected Amount', required=True, tracking=True)
    received_amount = fields.Float(string='Received Amount', tracking=True)
    outstanding_amount = fields.Float(string='Outstanding', compute='_compute_outstanding', store=True)

    status = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('received', 'Received'),
        ('overdue', 'Overdue'),
    ], string='Status', default='pending', tracking=True)

    due_date = fields.Date(string='Due Date', tracking=True)
    received_date = fields.Date(string='Received Date', tracking=True)
    notes = fields.Text(string='Notes')

    @api.depends('policy_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Commission / {rec.policy_id.policy_number or ''}"

    @api.depends('expected_amount', 'received_amount')
    def _compute_outstanding(self):
        for rec in self:
            rec.outstanding_amount = rec.expected_amount - (rec.received_amount or 0.0)

    def action_mark_received(self):
        self.write({
            'status': 'received',
            'received_amount': self.expected_amount,
            'received_date': date.today(),
        })

    def action_mark_partial(self):
        self.write({'status': 'partial'})

    def action_mark_overdue(self):
        self.write({'status': 'overdue'})

    @api.model
    def _cron_check_overdue(self):
        today = date.today()
        overdue = self.search([
            ('status', 'in', ['pending', 'partial']),
            ('due_date', '<', today),
        ])
        overdue.write({'status': 'overdue'})
