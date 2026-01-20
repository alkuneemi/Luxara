# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools import format_time
from odoo.tools.date_utils import float_to_time


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', 'Time Type', groups="hr.group_hr_user",
        domain="[('id', 'in', allowed_work_entry_type_ids)]", index="btree_not_null")
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids')
    display_code = fields.Char(related='work_entry_type_id.display_code')
    color = fields.Integer(related='work_entry_type_id.color')

    @api.depends('calendar_id.company_id')
    def _compute_allowed_work_entry_type_ids(self):
        for attendance in self:
            country = attendance.calendar_id.company_id.country_id or self.env.company.country_id
            if not country or not self.env['hr.work.entry.type'].search_count([('country_id', '=', country.id)], limit=1):
                domain = [('country_id', '=', False)]
            else:
                domain = [('country_id', '=', country.id)]
            attendance.allowed_work_entry_type_ids = self.env['hr.work.entry.type'].search(domain)

    def _compute_display_name(self):
        for attendance in self:
            if not attendance.work_entry_type_id:
                super()._compute_display_name()
            else:
                if attendance.duration_based:
                    attendance.display_name = self.env._("%(duration)s hours %(work_entry_type)s",
                                                        duration=format_time(self.env, float_to_time(attendance.duration_hours), time_format="HH:mm"),
                                                        work_entry_type=attendance.work_entry_type_id.display_name)
                else:
                    attendance.display_name = self.env._("%(hour_from)s - %(hour_to)s %(work_entry_type)s",
                                                        hour_from=format_time(self.env, float_to_time(attendance.hour_from), time_format="short"),
                                                        hour_to=format_time(self.env, float_to_time(attendance.hour_to), time_format="short"),
                                                        work_entry_type=attendance.work_entry_type_id.display_name)

    def _to_dict(self):
        res = super()._to_dict()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res

    def _is_work_period(self):
        self.ensure_one()
        return ((not self.sudo().work_entry_type_id) or self.sudo().work_entry_type_id.count_as == 'working_time') and super()._is_work_period()
