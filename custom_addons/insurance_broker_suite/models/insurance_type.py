from odoo import models, fields, api


class InsuranceType(models.Model):
    _name = 'insurance.type'
    _description = 'Insurance Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True, translate=True)
    name_ar = fields.Char(string='Arabic Name')
    category_id = fields.Many2one('insurance.category', string='Category', required=True, ondelete='restrict')
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(string='Published on Website', default=True)

    subtype_ids = fields.One2many('insurance.subtype', 'type_id', string='Sub-Types')
    subtype_count = fields.Integer(compute='_compute_subtype_count', string='Sub-Types')

    @api.depends('subtype_ids')
    def _compute_subtype_count(self):
        for rec in self:
            rec.subtype_count = len(rec.subtype_ids)
