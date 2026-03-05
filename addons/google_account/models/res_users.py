from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    google_account_email = fields.Char("Google Calendar Email", copy=False, groups='base.group_system')
