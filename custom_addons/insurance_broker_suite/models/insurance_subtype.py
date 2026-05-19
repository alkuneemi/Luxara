from odoo import models, fields, api


class InsuranceSubtype(models.Model):
    _name = 'insurance.subtype'
    _description = 'Insurance Sub-Type'
    _order = 'sequence, name'

    name = fields.Char(string='Sub-Type Name', required=True, translate=True)
    name_ar = fields.Char(string='Arabic Name')
    type_id = fields.Many2one('insurance.type', string='Insurance Type', required=True, ondelete='restrict')
    category_id = fields.Many2one('insurance.category', related='type_id.category_id', store=True, readonly=True, string='Category')
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(string='Published on Website', default=True)

    # Form type determines which fields are shown in the online application form
    form_type = fields.Selection([
        ('motor', 'Motor Insurance'),
        ('medical_individual', 'Medical - Individual'),
        ('medical_corporate', 'Medical - Corporate / Group'),
        ('property_fire', 'Property / Fire Insurance'),
        ('marine', 'Marine Insurance'),
        ('life', 'Life Insurance'),
        ('workmen', 'Workmen Compensation'),
        ('generic', 'Generic Form'),
    ], string='Form Type', required=True, default='generic',
        help='Determines which fields appear in the online application form.')

    # Required documents / documents checklist
    has_proposal_form = fields.Boolean(string='Proposal Form Required')
    has_comparison_sheet = fields.Boolean(string='Comparison Sheet Required')
    has_booking_slip = fields.Boolean(string='Booking Slip Required')
    additional_documents = fields.Text(string='Additional Required Documents',
        help='Comma-separated list of other required documents')

    # Notes shown to the customer on the form page
    customer_instructions = fields.Html(string='Customer Instructions')

    application_count = fields.Integer(compute='_compute_application_count', string='Applications')

    @api.depends()
    def _compute_application_count(self):
        for rec in self:
            rec.application_count = self.env['insurance.application'].search_count(
                [('subtype_id', '=', rec.id)]
            )
