# Part of Odoo. See LICENSE file for full copyright and licensing details.
import math
from collections import defaultdict
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import format_time
from odoo.tools.date_utils import float_to_time, parse_iso_date
from odoo.tools.intervals import Intervals
from odoo.tools.misc import format_date


def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y


def _check_collision(atti, attj):
    gcd, x0, _ = extended_gcd(atti['period'], attj['period'])
    delta_dates = (attj['date'] - atti['date']).days
    if delta_dates % gcd != 0:
        return None

    new_period = math.lcm(atti['period'], attj['period'])
    n_i_colide = (delta_dates * x0 // gcd) % (attj['period'] // gcd)
    new_date = relativedelta(days=atti['period'] * n_i_colide) + atti['date']
    start_date_max = max(atti['date'], attj['date'])
    if new_date < start_date_max:
        diff_days = (start_date_max - new_date).days
        nb_sauts = (diff_days + new_period - 1) // new_period
        new_date += relativedelta(days=nb_sauts * new_period)

    new_excluded = atti['excluded_ocurrences'] | attj['excluded_ocurrences']
    new_until = min(atti['until'], attj['until'])
    while str(new_date) in new_excluded:
        new_date += relativedelta(days=new_period)

    if new_date > new_until:
        return None

    return new_period, new_date, new_excluded, new_until


class ResourceCalendarAttendance(models.Model):
    _name = 'resource.calendar.attendance'
    _description = "Work Detail"
    _order = 'sequence, date, dayofweek, hour_from'

    hour_from = fields.Float(string='Work from', compute="_compute_hours", store=True, default=0,
        readonly=False, required=True, index=True, precompute=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to = fields.Float(string='Work to', compute="_compute_hours", store=True, default=0,
        readonly=False, required=True, precompute=True)
    # For the hour duration, the compute function is used to compute the value
    # unambiguously, while the duration in days is computed for the default
    # value but can be manually overridden.
    duration_hours = fields.Float(compute='_compute_duration_hours', string='Hours', store=True, readonly=False)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, index=True, ondelete='cascade')
    calendar_type = fields.Selection(related='calendar_id.calendar_type', readonly=True)
    duration_based = fields.Boolean(compute='_compute_duration_based', store=True, precompute=True)
    day_period = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('full_day', 'Full Day')], store=True, compute='_compute_day_period')
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the resource calendar.")

    # Fixed
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, precompute=True,
        compute="_compute_dayofweek", store=True, readonly=False)

    # Variable
    date = fields.Date()
    recurrency = fields.Boolean()
    recurrency_excluded_occurences = fields.Json()
    recurrency_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
    ], default='weeks')
    recurrency_interval = fields.Integer(string="Interval", default=1, help="Number of days or weeks between each occurrence.")
    recurrency_end_type = fields.Selection([
        ('forever', 'Forever'),
        ('times', 'Number of Occurrences'),
        ('date', 'Until'),
    ], default='forever', string="Recurrence End Condition")
    recurrency_count = fields.Integer(string="Number of Repetitions", default=1)
    recurrency_until = fields.Date(string="Recurrence End Date", compute="_compute_recurrency_until", store=True, readonly=False, precompute=True)

    _check_interval = models.Constraint(
        "CHECK(recurrency IS NOT TRUE OR recurrency_interval >= 1)",
        "The recurrency interval should be greater than 0",
    )

    _check_count = models.Constraint(
        "CHECK(recurrency IS NOT TRUE OR recurrency_end_type != 'times' OR recurrency_count > 0)",
        "The recurrency count should be greater than 0",
    )

    _check_recurrency_until = models.Constraint(
        "CHECK(recurrency_until IS NULL OR recurrency_until >= date)",
        "A recurrency should finish after the first occurence",
    )

    def _format_attendance(self):
        self.ensure_one()
        return {
            'ids': {self.id},
            'period': (self.recurrency_interval * 7 if self.recurrency_type == "weeks" else self.recurrency_interval) if self.recurrency else 0,
            'date': self.date,
            'excluded_ocurrences': set(self.recurrency_excluded_occurences or []),
            'until': self.recurrency_until,
            'max_id': self.id,
        }

    def _check_duration(self, date):
        if sum(self.mapped('duration_hours')) > 24:
            raise UserError(self.env._("Total duration of attendances cannot exceed 24 hours on %(date)s", date=format_date(self.env, date)))

    def _check_overlap(self, date):
        attendances_not_duration_based = self.filtered(lambda a: not a.duration_based)
        number_of_attendances = len(attendances_not_duration_based)
        number_of_distincts_intervals = len(Intervals([(att.hour_from, att.hour_to, att) for att in attendances_not_duration_based], keep_distinct=True))
        if number_of_attendances != number_of_distincts_intervals:
            raise UserError(self.env._("Overlap of attendances on %(date)s", date=format_date(self.env, date)))

    def _check_types(self, date):
        if len(set(self.mapped('duration_based'))) > 1:
            raise UserError(self.env._("You can't have duration based and time based attendances on the same day (on %(date)s)",
                                       date=format_date(self.env, date)))

    def _check_attendance(self, date):
        self._check_duration(date)
        self._check_overlap(date)
        self._check_types(date)

    def _check_attendances_variable(self):
        ids_to_check = set(self.ids)
        # Search to get all attendances that can be in conflict with the new ones
        if not (all_dates := [d for d in self.mapped('date') if d]):
            return
        min_date = min(all_dates)
        max_date_list = all_dates + [d.recurrency_until for d in self if d.recurrency]
        max_date = max(max_date_list)
        domain = Domain.AND([
            Domain('calendar_id', 'in', self.calendar_id.ids),
            Domain('calendar_id.calendar_type', '=', 'variable'),
            Domain.OR([
                Domain.AND([
                    Domain('recurrency', '=', True),
                    Domain('date', '<=', max_date),
                    Domain.OR([
                        Domain('recurrency_until', '=', False),
                        Domain('recurrency_until', '>=', min_date),
                    ])
                ]),
                Domain.AND([
                    Domain('recurrency', '=', False),
                    Domain('date', '>=', min_date),
                    Domain('date', '<=', max_date),
                ])
            ])
        ])
        attendances_by_calendar = self.env['resource.calendar.attendance'].search(domain, order='id asc').grouped('calendar_id')
        for _, attendances in attendances_by_calendar.items():
            recurrent_attendance_leaves = []
            ad_hoc_attendances = defaultdict(self.browse)
            for attendance in attendances:
                if attendance.recurrency:
                    recurrent_attendance_leaves.append(attendance._format_attendance())
                else:
                    ad_hoc_attendances[attendance.date] |= attendance
            # Build a collision tree for the reccurent attendances (all collisions with the new ones)
            collision_tree = list(recurrent_attendance_leaves)
            current_level_recurrent_attendance_nodes = list(recurrent_attendance_leaves)
            while current_level_recurrent_attendance_nodes:
                if len(collision_tree) > 1000:
                    raise UserError(self.env._("Too Complex Calendar"))
                next_level_recurrent_attendance_nodes = []
                for node_reccurency in current_level_recurrent_attendance_nodes:
                    for leaf_reccurency in recurrent_attendance_leaves:
                        # To not compare permuations of the same collisions
                        if node_reccurency['max_id'] >= leaf_reccurency['max_id']:
                            continue
                        collision = _check_collision(node_reccurency, leaf_reccurency)
                        if not collision:
                            continue
                        new_period, new_date, new_excluded, new_until = collision
                        new_ids = node_reccurency['ids'] | leaf_reccurency['ids']
                        # If new added reccurency is in the ids of this new recurrency, we check contraints
                        if not ids_to_check.isdisjoint(new_ids):
                            attendances = self.browse(new_ids)
                            attendances._check_attendance(new_date)
                        next_level_recurrent_attendance_nodes.append({
                            'ids': new_ids,
                            'period': new_period,
                            'date': new_date,
                            'excluded_ocurrences': new_excluded,
                            'until': new_until,
                            'max_id': leaf_reccurency['max_id'],
                        })
                collision_tree.extend(next_level_recurrent_attendance_nodes)
                current_level_recurrent_attendance_nodes = list(next_level_recurrent_attendance_nodes)

            # Use the collision tree for the ad hocs attendances
            for attendance_date, attendances in ad_hoc_attendances.items():
                ids_in_conflict = set()
                for node in collision_tree:
                    days_diff = (attendance_date - node['date']).days
                    if days_diff >= 0 and days_diff % node['period'] == 0:
                        if str(attendance_date) not in node['excluded_ocurrences']:
                            ids_in_conflict.update(node['ids'])
                if ids_in_conflict or attendances:
                    attendances_to_validate = attendances | self.browse(ids_in_conflict)
                    attendances_to_validate._check_attendance(attendance_date)

    def _check_attendances_fixed(self):
        domain = Domain.AND([
            Domain('calendar_id', 'in', self.calendar_id.ids),
            Domain('calendar_id.calendar_type', '=', 'fixed'),
            Domain('dayofweek', 'in', self.mapped('dayofweek')),
            Domain('date', '=', False),
        ])
        dayofweek_labels = dict(self._fields['dayofweek'].get_description(self.env)['selection'])
        other_attendances = self.env['resource.calendar.attendance'].search(domain, order='id asc')
        for _, all_attendances in other_attendances.grouped('calendar_id').items():
            for dayofweek, attendances in all_attendances.grouped('dayofweek').items():
                formated_date = dayofweek_labels[dayofweek]
                attendances._check_attendance(formated_date)

    @api.model_create_multi
    def create(self, vals_list):
        new_ids = super().create(vals_list)
        new_ids._check_attendances_variable()
        return new_ids

    def write(self, vals):
        res = super().write(vals)
        self._check_attendances_variable()
        return res

    @api.onchange('hour_from')
    def _onchange_hour_from(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)

    @api.onchange('hour_to')
    def _onchange_hour_to(self):
        # avoid negative or after midnight
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        if self.hour_from and not self.hour_to:
            self.hour_from = 0.0

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)

    @api.onchange('duration_hours')
    def _onchange_duration_hours(self):
        self.duration_hours = min(self.duration_hours, 24)
        if self.hour_from or self.hour_to:
            if self.hour_from + self.duration_hours > 24:
                self.hour_from = 24 - self.duration_hours
                self.hour_to = 24
            else:
                self.hour_to = self.hour_from + self.duration_hours

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_based(self):
        for attendance in self:
            attendance.duration_based = not attendance.hour_from and not attendance.hour_to

    @api.depends('duration_hours', 'hour_from', 'hour_to')
    def _compute_day_period(self):
        for attendance in self:
            if attendance.duration_hours > (0.75 * attendance.calendar_id.hours_per_day) or (not attendance.hour_from and not attendance.hour_to):
                attendance.day_period = 'full_day'
            elif attendance.hour_from and attendance.hour_to:
                if attendance.hour_from > 12 or (12 - attendance.hour_from <= attendance.hour_to - 12):
                    attendance.day_period = 'afternoon'
                else:
                    attendance.day_period = 'morning'
            else:
                attendance.day_period = 'morning'

    @api.depends('date')
    def _compute_dayofweek(self):
        for attendance in self:
            if attendance.date:
                attendance.dayofweek = str(attendance.date.weekday())
            elif not attendance.dayofweek:  # default value
                attendance.dayofweek = '0'

    @api.depends('hour_from', 'hour_to', 'duration_based')
    def _compute_duration_hours(self):
        for attendance in self:
            if not attendance.duration_based:
                attendance.duration_hours = max(0, attendance.hour_to - attendance.hour_from)

    @api.depends('duration_based')
    def _compute_hours(self):
        for attendance in self:
            if attendance.duration_based:
                attendance.hour_from = attendance.hour_to = 0

    @api.depends('recurrency', 'recurrency_end_type', 'recurrency_type', 'recurrency_interval', 'recurrency_count', 'date')
    def _compute_recurrency_until(self):
        for attendance in self:
            if not attendance.recurrency:
                attendance.recurrency_until = attendance.date
                continue
            match attendance.recurrency_end_type:
                case 'date' if attendance.recurrency_until == date.max:
                    attendance.recurrency_until = date.today()
                case 'times' if attendance.date and attendance.recurrency_type and attendance.recurrency_interval and attendance.recurrency_count:
                    attendance.recurrency_until = attendance.date + timedelta(**{attendance.recurrency_type: attendance.recurrency_interval * (attendance.recurrency_count - 1)})
                case 'forever':
                    attendance.recurrency_until = date.max

    def _compute_display_name(self):
        for attendance in self:
            if attendance.duration_based:
                attendance.display_name = self.env._("%(duration)s hours Attendance", duration=format_time(self.env, float_to_time(attendance.duration_hours), time_format="HH:mm"))
            else:
                attendance.display_name = self.env._("%(hour_from)s - %(hour_to)s Attendance",
                                                     hour_from=format_time(self.env, float_to_time(attendance.hour_from), time_format="short"),
                                                     hour_to=format_time(self.env, float_to_time(attendance.hour_to), time_format="short"))

    def _to_dict(self):
        self.ensure_one()
        return {
            'date': self.date,
            'dayofweek': self.dayofweek,
            'day_period': self.day_period,
            'duration_hours': self.duration_hours,
            'hour_from': self.hour_from,
            'hour_to': self.hour_to,
            'sequence': self.sequence,
        }

    def _is_work_period(self):
        self.ensure_one()
        return True

    def _filter_by_date(self, date: date):
        """
        Get the attendances for a specific date. For variable schedule, it will return the attendances with the same date or with a recurrency rule matching the date. For fixed schedule, it will return the attendances with the same day of week as the date.

        :param date
        """
        date_string = fields.Date.to_string(date)

        def date_filter(a):
            if a.recurrency:
                return a.recurrency_interval and (
                    date_string not in (a.recurrency_excluded_occurences or []) and a.date <= date <= a.recurrency_until
                    and (
                        (a.recurrency_type == 'days' and not (date - a.date).days % a.recurrency_interval)
                        or (a.recurrency_type == 'weeks' and not (date - a.date).days % 7 and not ((date - a.date).days // 7) % a.recurrency_interval)
                    )
                )
            return a.date == date if a.date else a.dayofweek == str(date.weekday())
        return self.filtered(date_filter)

    def _filter_between_dates(self, date_from, date_to):
        def _is_between_dates(att):
            att.ensure_one()
            if att.date:
                if att.recurrency:
                    return att.date <= date_to and att.recurrency_until >= date_from
                return date_from <= att.date <= date_to
            return not att.date

        return self.filtered(_is_between_dates)

    def exclude_occurence(self, date):
        self.ensure_one()
        if (parsed_date := parse_iso_date(date)) == self.date:
            new_date = parsed_date
            while new_date <= self.recurrency_until and new_date in [self.date] + (self.recurrency_excluded_occurences or []):
                new_date += relativedelta(days=self.recurrency_interval if self.recurrency_type == 'days' else self.recurrency_interval * 7)
            if new_date <= self.recurrency_until:
                if self.recurrency_end_type == 'times':
                    self.recurrency_end_type = 'date'
                self.date = new_date
            else:
                self.unlink()
                return
        excluded_ocurrences = self.recurrency_excluded_occurences or []
        if date not in excluded_ocurrences:
            excluded_ocurrences.append(date)
            self.recurrency_excluded_occurences = excluded_ocurrences

    def exclude_multiple_occurences(self, dates):
        for attendance in self:
            for date_to_exclude in dates:
                attendance.exclude_occurence(date_to_exclude)

    def stop_recurrency(self, date):
        self.ensure_one()
        self.update({
            'recurrency_until': parse_iso_date(date) - relativedelta(days=1),
            'recurrency_end_type': 'date',
        })

    def create_ad_hoc(self, date, changes):
        self.ensure_one()
        data = self.copy_data()[0]
        self.exclude_occurence(date)
        new_data = {
            **data,
            **changes,
            'date': parse_iso_date(date),
        }
        new_data_without_recurrency = {f: v for f, v in new_data.items() if "recurrency" not in f}
        return self.create(new_data_without_recurrency)

    def create_new_recurrency(self, date, changes):
        self.ensure_one()
        data = self.copy_data()[0]
        self.stop_recurrency(date)
        new_data = {
            **data,
            **changes,
            'date': parse_iso_date(date),
        }
        if ('recurrency_end_type' in new_data and 'recurrency_until' in new_data
            and (new_data['recurrency_end_type'] != 'date' or not new_data['recurrency_until'])):
            del new_data['recurrency_until']
        return self.create(new_data)
