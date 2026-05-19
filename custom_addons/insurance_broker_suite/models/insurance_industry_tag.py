from odoo import models, fields


class InsuranceIndustryTag(models.Model):
      _name = 'insurance.industry.tag'
      _description = 'Insurance Client Industry / Sector'
      _order = 'name'

      name = fields.Char(string='Industry / Sector', required=True, translate=True)
      name_ar = fields.Char(string='Arabic Name / الاسم بالعربي')
      active = fields.Boolean(default=True)
      color = fields.Integer(string='Color Index', default=0)

      _sql_constraints = [
          ('name_uniq', 'unique(name)', 'Industry name must be unique!'),
      ]
  
