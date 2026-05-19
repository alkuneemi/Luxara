from odoo import models, fields, api


class InsuranceCategory(models.Model):
    _name = 'insurance.category'
    _description = 'Insurance Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    name_ar = fields.Char(string='Arabic Name')
    description = fields.Text(string='Description', translate=True)
    icon = fields.Char(string='Icon (FontAwesome)', default='fa-shield')
    color = fields.Char(string='Color (hex)', default='#3b82f6')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(string='Published on Website', default=True)
    image = fields.Image(string='Category Image', max_width=512, max_height=512)

    type_ids = fields.One2many('insurance.type', 'category_id', string='Insurance Types')
    type_count = fields.Integer(compute='_compute_type_count', string='Types')

    @api.depends('type_ids')
    def _compute_type_count(self):
        for rec in self:
            rec.type_count = len(rec.type_ids)

    def action_view_types(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insurance Types',
            'res_model': 'insurance.type',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
