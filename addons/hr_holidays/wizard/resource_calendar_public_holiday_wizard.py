# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
from collections import defaultdict
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from markupsafe import Markup, escape

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import file_open, file_path
from odoo.tools.date_utils import convert_timezone


class ResourceCalendarPublicHolidayWizard(models.TransientModel):
    _name = 'resource.calendar.public.holiday.wizard'
    _description = 'Public Holiday Preview Wizard'

    year = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    calendar_id = fields.Many2one(
        'resource.calendar',
        string="Working Schedule",
        domain=lambda self: ['|', ('company_id', '=', False), ('company_id', 'in', self._get_companies().ids)],
    )
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string="Work Entry Type")
    warning_message = fields.Html(compute='_compute_warning_message')
    line_ids = fields.One2many(
        'resource.calendar.public.holiday.wizard.line',
        'wizard_id',
        string="Public Holidays",
        compute='_compute_line_ids',
        store=True,
        readonly=False,
    )

    def _get_companies(self):
        company_ids = self.env.context.get('public_holiday_company_ids') or self.env.companies.ids
        return self.env['res.company'].browse(company_ids).exists()

    def _get_holidays_from_csv(self, year, csv_file_path):
        holidays = []
        with file_open(csv_file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("date") or not row.get("holiday"):
                    continue
                holiday_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
                if holiday_date.year > year:
                    break
                if holiday_date.year == year:
                    holidays.append((holiday_date, row["holiday"].strip()))
        return holidays

    def _prepare_public_holidays_data(self):
        companies = self._get_companies()
        prepared_public_holidays = {}
        companies_without_country = self.env['res.company']
        companies_without_public_holidays = self.env['res.company']
        companies_with_all_existing_holidays = self.env['res.company']
        existing_holidays_dict = dict(self.env["resource.calendar.leaves"]._read_group(
            domain=[
                ('company_id', 'in', companies.ids),
                ('date_from', '>=', datetime(self.year - 1, 12, 31, 0, 0, 0)),
                ('date_to', '<=', datetime(self.year + 1, 1, 2, 0, 0, 0)),
                ('resource_id', '=', False),
            ],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        ))

        for company in companies:
            if not company.country_code:
                companies_without_country |= company
                continue

            try:
                csv_file_path = file_path(f"hr_holidays/data/public_holidays/public_holidays_{company.country_code.lower()}.csv")
            except FileNotFoundError:
                companies_without_public_holidays |= company
                continue

            public_holidays_list = self._get_holidays_from_csv(self.year, csv_file_path)
            if not public_holidays_list:
                companies_without_public_holidays |= company
                continue

            company_tz = ZoneInfo(company.tz or self.env.user.tz or 'UTC')
            public_holidays_values_dict = {}

            for holiday_date, holiday_name in public_holidays_list:
                holiday_start_utc = convert_timezone(datetime.combine(holiday_date, time.min), UTC, company_tz)
                holiday_end_utc = convert_timezone(datetime.combine(holiday_date, time.max), UTC, company_tz)
                overlapping = any(
                    holiday.date_from <= holiday_end_utc and
                    holiday.date_to >= holiday_start_utc
                    for holiday in existing_holidays_dict.get(company, [])
                )
                if overlapping:
                    continue
                if holiday_date in public_holidays_values_dict:
                    public_holidays_values_dict[holiday_date]['name'] += f" / {holiday_name}"
                else:
                    public_holidays_values_dict[holiday_date] = {
                        'name': holiday_name,
                        'start_date': holiday_date,
                        'end_date': holiday_date,
                        'company_id': company.id,
                    }

            if public_holidays_values_dict:
                prepared_public_holidays[company.id] = {
                    'values': list(public_holidays_values_dict.values()),
                }
            else:
                companies_with_all_existing_holidays |= company

        return {
            'prepared_public_holidays': prepared_public_holidays,
            'companies_without_country': companies_without_country,
            'companies_without_public_holidays': companies_without_public_holidays,
            'companies_with_all_existing_holidays': companies_with_all_existing_holidays,
        }

    def _get_line_commands(self):
        self.ensure_one()
        prepared_public_holidays = self._prepare_public_holidays_data()
        preview_values = [
            public_holiday_value
            for company_data in prepared_public_holidays['prepared_public_holidays'].values()
            for public_holiday_value in company_data['values']
        ]
        return [
            Command.create({
                'name': preview_value['name'],
                'start_date': preview_value['start_date'],
                'end_date': preview_value['end_date'],
                'company_id': preview_value['company_id'],
            })
            for preview_value in preview_values
        ]

    @api.constrains('year')
    def _check_year(self):
        for wizard in self:
            if wizard.year < 1:
                raise ValidationError(self.env._("The year must be greater than 0."))

    @api.depends('year')
    def _compute_line_ids(self):
        for wizard in self:
            commands = [Command.clear()]
            if wizard.year:
                commands.extend(wizard._get_line_commands())
            wizard.line_ids = commands

    @api.depends('year')
    def _compute_warning_message(self):
        for wizard in self:
            wizard.warning_message = False
            if wizard.year:
                prepared_public_holidays = wizard._prepare_public_holidays_data()
                wizard.warning_message = wizard._format_warning_message(
                    wizard._get_warning_messages(prepared_public_holidays),
                )

    def _format_company_names(self, companies):
        return ', '.join(companies.mapped('name'))

    def _get_warning_messages(self, prepared_public_holidays):
        self.ensure_one()
        warning_messages = []
        if prepared_public_holidays['companies_with_all_existing_holidays']:
            warning_messages.append(self.env._(
                "All public holidays for %(year)s are already present for: %(companies)s.",
                year=self.year,
                companies=self._format_company_names(prepared_public_holidays['companies_with_all_existing_holidays']),
            ))
        if prepared_public_holidays['companies_without_country']:
            warning_messages.append(self.env._(
                "These companies do not have a country set: %(companies)s.",
                companies=self._format_company_names(prepared_public_holidays['companies_without_country']),
            ))
        if prepared_public_holidays['companies_without_public_holidays']:
            warning_messages.append(self.env._(
                "Public holiday data is not available for %(year)s for: %(companies)s.",
                year=self.year,
                companies=self._format_company_names(prepared_public_holidays['companies_without_public_holidays']),
            ))
        return warning_messages

    def _format_warning_message(self, warning_messages):
        if not warning_messages:
            return False
        return Markup('<ul class="mb-0">%s</ul>') % Markup('').join(
            Markup('<li>%s</li>') % escape(warning_message)
            for warning_message in warning_messages
        )

    def _get_create_values_by_company(self):
        self.ensure_one()
        values_by_company = defaultdict(list)
        companies = self._get_companies()
        for line in self.line_ids:
            company = line.company_id
            if company not in companies:
                continue
            company_tz = ZoneInfo(company.tz or self.env.user.tz or 'UTC')
            create_values = {
                'name': line.name,
                'date_from': convert_timezone(datetime.combine(line.start_date, time.min), UTC, company_tz),
                'date_to': convert_timezone(datetime.combine(line.end_date, time.max), UTC, company_tz),
                'company_id': company.id,
            }
            if self.calendar_id:
                create_values['calendar_id'] = self.calendar_id.id
            if self.work_entry_type_id:
                create_values.update({
                    'work_entry_type_id': self.work_entry_type_id.id,
                    'count_as': self.work_entry_type_id.count_as,
                    'elligible_for_accrual_rate': self.work_entry_type_id.elligible_for_accrual_rate,
                })
            values_by_company[company.id].append(create_values)
        return values_by_company

    def action_add_public_holidays(self):
        self.ensure_one()
        prepared_public_holidays = self._prepare_public_holidays_data()
        warning_messages = self._get_warning_messages(prepared_public_holidays)
        notification_messages = []
        convert_datetime = self.env.context.get('public_holiday_convert_datetime', True)
        for company_id, create_values in self._get_create_values_by_company().items():
            company = self.env['res.company'].browse(company_id)
            created_leaves = self.env['resource.calendar.leaves'].with_context(convert_datetime=convert_datetime).create(create_values)
            if created_leaves:
                notification_messages.append(self.env._(
                    'Created %(count)s public holiday%(suffix)s for %(company)s.',
                    count=len(created_leaves),
                    suffix='' if len(created_leaves) == 1 else 's',
                    company=company.name,
                ))
        notification_messages.extend(warning_messages)
        next_action = {'type': 'ir.actions.act_window_close'}
        if self.env.context.get('params', {}).get('view_type') == 'list':
            next_action = {'type': 'ir.actions.client', 'tag': 'reload'}
        notification_type = 'success' if notification_messages and not warning_messages else 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notification_type,
                'message': '\n'.join(notification_messages) or self.env._("No public holidays were added."),
                'next': next_action,
            },
        }


class ResourceCalendarPublicHolidayWizardLine(models.TransientModel):
    _name = 'resource.calendar.public.holiday.wizard.line'
    _description = 'Public Holiday Preview Wizard Line'
    _order = 'company_id, start_date, name'

    wizard_id = fields.Many2one('resource.calendar.public.holiday.wizard', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    company_id = fields.Many2one('res.company', required=True)
