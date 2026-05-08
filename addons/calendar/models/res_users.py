# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from zoneinfo import ZoneInfo

from odoo import api, fields, models, modules, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    calendar_ids = fields.One2many('calendar.calendar', 'user_id', string='Calendars')

    @api.constrains('calendar_ids')
    def _check_calendar_ids(self):
        for record in self:
            if len(record.calendar_ids.filtered(lambda c: c.is_primary)) > 1:
                raise ValidationError(_("A user can only have one primary calendar"))

    def get_selected_calendars_partner_ids(self, include_user=True):
        """
        Retrieves the partner IDs of the attendees selected in the calendar view.

        :param bool include_user: Determines whether to include the current user's partner ID in the results.
        :return: A list of integer IDs representing the partners selected in the calendar view.
                 If 'include_user' is True, the list will also include the current user's partner ID.
        :rtype: list
        """
        self.ensure_one()
        partner_ids = self.env['calendar.filters'].search([
            ('user_id', '=', self.id),
            ('partner_checked', '=', True)
        ]).partner_id.ids

        if include_user:
            partner_ids += [self.env.user.partner_id.id]
        return partner_ids

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        default_privacy = self.env['ir.config_parameter'].sudo().get_str('calendar.default_privacy', 'public')
        calendar_vals_list = [
            {
                'user_id': user.id,
                'name': 'Primary Calendar',
                'is_primary': True,
                'calendar_default_privacy': default_privacy,
            }
            for user in users
        ]
        calendars = self.env['calendar.calendar'].create(calendar_vals_list)
        filter_vals_list = [
            {
                'user_id': user.id,
                'calendar_id': calendar.id,
                'active': True,
                'is_checked': True,
            }
            for user, calendar in zip(users, calendars)
        ]
        self.env['calendar.calendar.filter'].create(filter_vals_list)
        return users

    def _systray_get_calendar_event_domain(self):
        # Determine the domain for which the users should be notified. This method sends notification to
        # events occurring between now and the end of the day. Note that "now" needs to be computed in the
        # user TZ and converted into UTC to compare with the records values and "the end of the day" needs
        # also conversion. Otherwise TZ diverting a lot from UTC would send notification for events occurring
        # tomorrow.
        # The user is notified if the start is occurring between now and the end of the day
        # if the event is not finished.
        #   |           |
        #   |===========|===> DAY A (`start_dt`): now in the user TZ
        #   |           |
        #   |           | <--- `start_dt_utc`: now is on the right if the user lives
        #   |           |               in West Longitude (America for example)
        #   |           |
        #   |  -------  | <--- `start`: the start of the event (in UTC)
        #   | | event | |
        #   |  -------  | <--- `stop`: the stop of the event (in UTC)
        #   |           |
        #   |           |
        #   |           | <--- `stop_dt_utc` = `stop_dt` if user lives in an area of East longitude (positive shift compared to UTC, Belgium for example)
        #   |           |
        #   |           |
        #   |-----------| <--- `stop_dt` = end of the day for DAY A from user point of view (23:59 in this TZ)
        #   |===========|===> DAY B
        #   |           |
        #   |           | <--- `stop_dt_utc` = `stop_dt` if user lives in an area of West longitude (positive shift compared to UTC, America for example)
        #   |           |
        start_dt_utc = start_dt = datetime.datetime.now(datetime.UTC)
        stop_dt_utc = datetime.datetime.combine(start_dt_utc.date(), datetime.time.max.replace(tzinfo=datetime.UTC))

        tz = self.env.user.tz
        if tz:
            user_tz = ZoneInfo(tz)
            start_dt = start_dt_utc.astimezone(user_tz)
            stop_dt = datetime.datetime.combine(start_dt.date(), datetime.time.max.replace(tzinfo=user_tz, fold=1))
            stop_dt_utc = stop_dt.astimezone(datetime.UTC)

        start_date = start_dt.date()

        current_user_non_declined_attendee_ids = self.env['calendar.attendee']._search([
            ('partner_id', '=', self.env.user.partner_id.id),
            ('state', '!=', 'declined'),
        ])

        return ['&', '|',
                '&',
                    '|',
                        ['start', '>=', fields.Datetime.to_string(start_dt_utc)],
                        ['stop', '>=', fields.Datetime.to_string(start_dt_utc)],
                    ['start', '<=', fields.Datetime.to_string(stop_dt_utc)],
                '&',
                    ['allday', '=', True],
                    ['start_date', '=', fields.Date.to_string(start_date)],
                ('attendee_ids', 'in', current_user_non_declined_attendee_ids)]

    @api.model
    def _get_activity_groups(self):
        res = super()._get_activity_groups()
        EventModel = self.env['calendar.event']
        meetings_lines = EventModel.search_read(
            self._systray_get_calendar_event_domain(),
            ['id', 'start', 'name', 'allday'],
            order='start')
        if meetings_lines:
            meeting_label = _("Today's Meetings")
            meetings_systray = {
                'id': self.env['ir.model']._get('calendar.event').id,
                'type': 'meeting',
                'name': meeting_label,
                'is_today_meetings': True,
                'model': 'calendar.event',
                'icon': modules.module.get_module_icon(EventModel._original_module),
                'domain': [('active', 'in', [True, False])],
                'meetings': meetings_lines,
                "view_type": EventModel._systray_view,
            }
            res.insert(0, meetings_systray)
        return res

    @api.model
    def check_calendar_credentials(self):
        return {}

    def get_calendar_email(self):
        """Meant to be overridden by a specific calendar provider"""
        return False

    def check_synchronization_status(self):
        return {}

    def _has_any_active_synchronization(self):
        """
        Overridable method for checking if user has any synchronization active in inherited modules.

        :return: boolean indicating if any synchronization is active.
        """
        return False
