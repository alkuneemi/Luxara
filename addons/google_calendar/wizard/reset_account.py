# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class GoogleCalendarAccountReset(models.TransientModel):
    _name = 'google.calendar.account.reset'
    _description = 'Google Calendar Account Reset'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    delete_policy = fields.Selection(
        [('dont_delete', "Keep all events (recommended)"),
         ('delete_odoo', "Delete synced events from Odoo"),
        ], string="User's Existing Events", required=True, default='dont_delete',
        help="This will only affect events for which the user is the owner")

    calendar_delete_policy = fields.Selection(
        [('dont_delete', "Keep all calendars (they wil not be synchronized with a different account)"),
         ('delete_odoo', "Delete synced calendars from Odoo"),
        ], string="User's Existing Calendars", required=True, default='dont_delete',
        help="This will only affect calendars for which the user is the owner")

    def reset_account(self):
        self.user_id.res_users_settings_id._set_google_auth_tokens(False, False, 0)
        self.user_id.res_users_settings_id.sudo().write({
            'google_calendar_sync_token': False,
        })
        self.user_id.calendar_ids.sudo().write({
            'google_sync_token': False,
        })

        if self.delete_policy == 'delete_odoo':
            events = self.env['calendar.event'].search([
                ('user_id', '=', self.user_id.id),
                ('google_id', '!=', False)])
            recurrences = self.env['calendar.recurrence'].search([
                ('base_event_id', 'in', events.ids),
                ('google_id', '!=', False)])

            # Flag need_sync as False in order to skip the write permission when resetting.
            events.with_context(skip_event_permission=True).google_id = False
            recurrences.with_context(skip_event_permission=True).google_id = False
            events.unlink()

        if self.calendar_delete_policy == 'delete_odoo':
            calendars = self.user_id.calendar_ids.filtered(lambda c: c.google_id and not c.is_primary)
            calendars.google_id = False
            calendars.unlink()

        self.user_id.stop_google_synchronization()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
