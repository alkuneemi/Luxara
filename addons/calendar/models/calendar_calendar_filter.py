# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class CalendarCalendarFilter(models.Model):
    _name = 'calendar.calendar.filter'
    _description = 'Calendar Filter'

    _unique_filter_per_user_calendar = models.UniqueIndex('(user_id, calendar_id)')

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade",
        default=lambda self: self.env.user)
    calendar_id = fields.Many2one('calendar.calendar', index='btree', ondelete="cascade", required=True,
        domain=lambda self: [('user_id', '=', self.user_id.id)])
    is_primary = fields.Boolean(related="calendar_id.is_primary")
    color = fields.Integer(related='calendar_id.color')
    active = fields.Boolean('Active', default=True)
    is_checked = fields.Boolean('Checked', default=True)
