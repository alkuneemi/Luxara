from odoo import models, fields, api
from datetime import date, timedelta


class InsuranceRfq(models.Model):
    _name = 'insurance.rfq'
    _description = 'Request for Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference_no'
    _order = 'create_date desc'

    reference_no = fields.Char(
        string='Reference No.', required=True, copy=False,
        readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('insurance.rfq')
    )
    client_id = fields.Many2one('insurance.client', string='Client', required=True, tracking=True, ondelete='restrict')

    # Link back to originating application
    application_id = fields.Many2one(
        'insurance.application', string='Source Application',
        ondelete='set null', tracking=True, index=True,
    )

    insurance_type = fields.Selection([
        ('motor', 'Motor'),
        ('medical', 'Medical'),
        ('life', 'Life'),
        ('property', 'Property'),
        ('marine', 'Marine'),
        ('group_life', 'Group Life'),
        ('workmen_compensation', 'Workmen Compensation'),
    ], string='Insurance Type', required=True, tracking=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('responses_received', 'Responses Received'),
        ('comparison_ready', 'Comparison Ready'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    sent_date = fields.Date(string='Date Sent')
    response_deadline = fields.Date(string='Response Deadline')
    underwriting_complete = fields.Boolean(string='Underwriting Complete', tracking=True)
    notes = fields.Text(string='Notes / Requirements')
    requirements_summary = fields.Html(string='Requirements Summary')

    quote_ids = fields.One2many('insurance.rfq.quote', 'rfq_id', string='Insurer Quotes')
    quote_count = fields.Integer(compute='_compute_quote_count', string='Quotes')
    recommended_quote_id = fields.Many2one('insurance.rfq.quote', string='Recommended Quote')

    policy_id = fields.Many2one('insurance.policy', string='Resulting Policy', readonly=True)

    # Providers this RFQ was sent to
    provider_ids = fields.Many2many(
        'insurance.company.provider',
        'rfq_provider_rel',
        'rfq_id', 'provider_id',
        string='Providers Notified',
        tracking=True,
    )
    provider_count = fields.Integer(compute='_compute_provider_count', string='Providers Notified')

    @api.depends('quote_ids')
    def _compute_quote_count(self):
        for rec in self:
            rec.quote_count = len(rec.quote_ids)

    @api.depends('provider_ids')
    def _compute_provider_count(self):
        for rec in self:
            rec.provider_count = len(rec.provider_ids)

    def action_send(self):
        self.write({'status': 'sent', 'sent_date': date.today()})

    def action_mark_responses_received(self):
        self.write({'status': 'responses_received'})

    def action_generate_comparison(self):
        self.ensure_one()
        if len(self.quote_ids) < 2:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Cannot Compare',
                    'message': 'Please add at least 2 insurer quotes before generating a comparison.',
                    'type': 'warning',
                }
            }
        self.write({'status': 'comparison_ready'})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Comparison',
            'res_model': 'insurance.comparison.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_rfq_id': self.id},
        }

    def action_close(self):
        self.write({'status': 'closed'})

    def action_view_quotes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotes',
            'res_model': 'insurance.rfq.quote',
            'view_mode': 'list,form',
            'domain': [('rfq_id', '=', self.id)],
            'context': {'default_rfq_id': self.id},
        }

    def action_send_to_providers(self):
        """Find relevant active providers and send them an RFQ invitation email."""
        self.ensure_one()
        # Match providers by category (linked to the application)
        category_id = self.application_id.category_id.id if self.application_id else False
        type_id = self.application_id.type_id.id if self.application_id else False

        domain = [('portal_active', '=', True), ('active', '=', True)]
        all_providers = self.env['insurance.company.provider'].sudo().search(domain)

        # Prefer providers that explicitly list the category or type
        if category_id:
            filtered = all_providers.filtered(lambda p: category_id in p.category_ids.ids)
            if filtered:
                all_providers = filtered
        if type_id and len(all_providers) > 3:
            filtered2 = all_providers.filtered(lambda p: type_id in p.type_ids.ids)
            if filtered2:
                all_providers = filtered2

        if not all_providers:
            return False

        self.write({
            'provider_ids': [(6, 0, all_providers.ids)],
            'status': 'sent',
            'sent_date': date.today(),
            'response_deadline': date.today() + timedelta(days=5),
        })

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        ins_label = dict(self._fields['insurance_type'].selection).get(self.insurance_type, self.insurance_type)

        for provider in all_providers:
            if not provider.email or not provider.portal_token:
                continue
            rfq_url = f'{base_url}/insurance/provider/rfq/{self.id}?token={provider.portal_token}'
            self.env['mail.mail'].sudo().create({
                'subject': f'[RFQ] {self.reference_no} — {ins_label} Insurance Quote Request',
                'email_to': provider.email,
                'body_html': f'''
                    <div style="font-family:Arial,sans-serif;max-width:600px">
                    <div style="background:#059669;padding:20px;border-radius:8px 8px 0 0">
                        <h2 style="color:#fff;margin:0">New Quote Request</h2>
                        <p style="color:#d1fae5;margin:4px 0 0">Ameen Hub Insurance Brokerage</p>
                    </div>
                    <div style="background:#f9fafb;padding:24px;border-radius:0 0 8px 8px;border:1px solid #e5e7eb">
                        <p>Dear <strong>{provider.name}</strong>,</p>
                        <p>We have a new <strong>{ins_label}</strong> insurance quote request for your review.</p>
                        <table style="width:100%;border-collapse:collapse;margin:16px 0">
                            <tr><td style="padding:8px;background:#fff;border:1px solid #e5e7eb;font-weight:bold">RFQ Reference</td>
                                <td style="padding:8px;background:#fff;border:1px solid #e5e7eb">{self.reference_no}</td></tr>
                            <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:bold">Insurance Type</td>
                                <td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb">{ins_label}</td></tr>
                            <tr><td style="padding:8px;background:#fff;border:1px solid #e5e7eb;font-weight:bold">Date Sent</td>
                                <td style="padding:8px;background:#fff;border:1px solid #e5e7eb">{self.sent_date}</td></tr>
                            <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:bold">Response Deadline</td>
                                <td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;color:#dc2626;font-weight:bold">{self.response_deadline}</td></tr>
                        </table>
                        <div style="text-align:center;margin:24px 0">
                            <a href="{rfq_url}" style="background:#059669;color:#fff;padding:14px 32px;border-radius:8px;
                               text-decoration:none;font-weight:bold;font-size:16px;display:inline-block">
                                View RFQ &amp; Submit Quote
                            </a>
                        </div>
                        <p style="color:#6b7280;font-size:13px">
                            This link is unique to your organisation. Please do not share it.<br>
                            If you prefer API integration, visit your provider portal for API documentation.
                        </p>
                    </div></div>
                ''',
            }).send()
        return True
