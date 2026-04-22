# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging


from odoo import api, fields, models, Command
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService, InvalidSyncToken
from odoo.addons.google_calendar.models.google_sync import google_calendar_token
from odoo.addons.google_account.models import google_service
from odoo.exceptions import LockError
from odoo.fields import Domain
from odoo.loglevels import exception_to_unicode

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    google_calendar_email = fields.Char(related='res_users_settings_id.google_calendar_email')
    google_calendar_rtoken = fields.Char(related='res_users_settings_id.google_calendar_rtoken', groups="base.group_system")
    google_calendar_token = fields.Char(related='res_users_settings_id.google_calendar_token', groups="base.group_system")
    google_calendar_token_validity = fields.Datetime(related='res_users_settings_id.google_calendar_token_validity', groups="base.group_system")
    google_calendar_sync_token = fields.Char(related='res_users_settings_id.google_calendar_sync_token', groups="base.group_system")
    google_synchronization_stopped = fields.Boolean(related='res_users_settings_id.google_synchronization_stopped', readonly=False, groups="base.group_system")
    google_synchronization_needs_reset = fields.Boolean(related='res_users_settings_id.google_synchronization_needs_reset', readonly=False)

    def _get_google_calendar_token(self):
        self.ensure_one()
        if self.res_users_settings_id.sudo().google_calendar_rtoken and not self.res_users_settings_id._is_google_calendar_valid():
            self.sudo().res_users_settings_id._refresh_google_calendar_token()
        return self.res_users_settings_id.sudo().google_calendar_token

    def _get_google_sync_status(self):
        """ Returns the calendar synchronization status (active, paused or stopped). """
        status = "sync_active"
        if self.env['ir.config_parameter'].sudo().get_bool("google_calendar_sync_paused"):
            status = "sync_paused"
        elif self.sudo().google_calendar_rtoken and not self.sudo().google_synchronization_stopped:
            status = "sync_active"
        elif self.sudo().google_synchronization_stopped:
            status = "sync_stopped"
        return status

    def _check_pending_odoo_records(self):
        """ Returns True if sync is active and there are records to be synchronized to Google. """
        if self._get_google_sync_status() != "sync_active":
            return False
        pending_events = self.env['calendar.event']._check_any_records_to_sync()
        pending_recurrences = self.env['calendar.recurrence']._check_any_records_to_sync()
        return pending_events or pending_recurrences

    def _sync_calendars_request(self, calendar_service: GoogleCalendarService):
        if self._get_google_sync_status() != "sync_active":
            return False
        # don't attempt to sync when another sync is already in progress, as we wouldn't be
        # able to commit the transaction anyway (row is locked)
        self.ensure_one()
        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            _logger.info("skipping calendar sync, locked user %s", self.login)
            return False

        with google_calendar_token(self) as token:
            # Google -> Odoo
            try:
                calendars, data = calendar_service.get_calendars(sync_token=self.res_users_settings_id.sudo().google_calendar_sync_token, token=token)
            except InvalidSyncToken:
                calendars, data = calendar_service.get_calendars(token=token)

            if data.get('nextSyncToken', False):
                self.res_users_settings_id.sudo().google_calendar_sync_token = data.get('nextSyncToken')

            return calendars

    def _get_calendars_to_sync(self):
        sync_domain = (Domain([('is_readonly', '=', False), ('user_id', '=', self.id)]) & (Domain('need_sync', '=', True)
                     | Domain([('google_id', '=', False), ('is_primary', '=', False)])))
        return self.env['calendar.calendar'].search(sync_domain)

    def _sync_google_calendars(self, calendar_service: GoogleCalendarService):
        # Google -> Odoo
        google_calendar_values = self._sync_calendars_request(calendar_service)
        self.calendar_ids.with_user(self)._sync_calendars_google2odoo(google_calendar_values)

        # Odoo -> Google
        # Local calendars, which have not yet been synchronized with Google or need to be updated
        self._get_calendars_to_sync().with_user(self)._sync_calendars_odoo2google(calendar_service)

    def _is_cancelled(self, event, active_events):
        return event.cancelled() and event.id not in active_events

    def _sync_google_calendar(self, calendar_service: GoogleCalendarService):
        self.ensure_one()

        self._sync_google_calendars(calendar_service)
        # Commit calendar changes so that the @after_commit calls to the Google API are performed before
        # continuing with event sync.
        self.env.cr.commit()

        need_refresh = False
        synced_recurrences = self.env['calendar.recurrence']
        synced_events = self.env['calendar.event']

        events_per_calendar = {}

        # Google -> Odoo
        # Fetch events for all calendars, before processing them.
        for calendar in self.env.user.calendar_ids:
            results = self._sync_request(calendar_service, calendar=calendar)
            if not results:
                continue

            events, default_reminders, full_sync = results.values()
            events = self._sync_google_calendar_filter_remote_events(events)

            if not events:
                continue

            events.clear_type_ambiguity(self.env)
            recurrences = events.filter(lambda e: e.is_recurrence())
            normal_events = events - recurrences

            events_per_calendar[calendar.id] = {
                'calendar': calendar,
                'events': normal_events,
                'recurrences': recurrences,
                'default_reminders': default_reminders,
                'full_sync': full_sync,
            }

        # When moving an event from one calendar to another, Google will send a cancellation event for the
        # original calendar, and an update event for the new one. We need to make sure that we don't cancel the
        # event in Odoo if it only moved. To do this, we keep track of all active events and ignore any
        # cancellation for those which are still active in some calendar.
        active_events = set()
        active_recurrences = set()
        for calendar_id, calendar_data in events_per_calendar.items():
            for event in calendar_data.get('events', []):
                if not event.cancelled():
                    active_events.add(event.id)
            for recurrence in calendar_data.get('recurrences', []):
                if not recurrence.cancelled():
                    active_recurrences.add(recurrence.id)

        for calendar_id, calendar_data in events_per_calendar.items():
            events = calendar_data.get('events', [])
            calendar = calendar_data.get('calendar', [])
            recurrences = calendar_data.get('recurrences', [])
            default_reminders = calendar_data.get('default_reminders', [])

            # We need to filter out fake cancelled events that are still active in another calendar.
            fake_cancelled_events = events.filter(lambda e: e.cancelled() and e.id in active_events)
            events_to_sync = events - recurrences - fake_cancelled_events
            fake_cancelled_recurrences = recurrences.filter(lambda e: e.cancelled() and e.id in active_events)
            recurrences_to_sync = recurrences - fake_cancelled_recurrences

            # We apply Google updates only if their write date is later than the write date in Odoo.
            # It's possible that multiple updates affect the same record, maybe not directly.
            # To handle this, we preserve the write dates in Odoo before applying any updates,
            # and use these dates instead of the current live dates.
            odoo_events = self.env['calendar.event'].browse(events_to_sync.odoo_ids(self.env))
            odoo_recurrences = self.env['calendar.recurrence'].browse(recurrences_to_sync.odoo_ids(self.env))
            recurrences_write_dates = {r.id: r.write_date for r in odoo_recurrences}
            events_write_dates = {e.id: e.write_date for e in odoo_events}

            synced_recurrences |= self.env['calendar.recurrence']._sync_google2odoo(recurrences_to_sync, recurrences_write_dates, calendar)
            synced_events |= self.env['calendar.event']._sync_google2odoo(events_to_sync, events_write_dates, calendar, default_reminders=default_reminders)

        if not self._check_pending_odoo_records():
            return synced_recurrences or synced_events

        # Odoo -> Google
        for calendar in self.env.user.calendar_ids:
            if calendar.is_readonly:
                continue
            full_sync = events_per_calendar.get(calendar.id, {}).get('full_sync', False)
            send_updates = not full_sync
            recurrences = self.env['calendar.recurrence']._get_records_to_sync(calendar, full_sync=full_sync)
            recurrences -= synced_recurrences
            recurrences.with_context(send_updates=send_updates)._sync_odoo2google(calendar_service)
            synced_events |= recurrences.calendar_event_ids - recurrences._get_outliers()
            synced_events |= synced_recurrences.calendar_event_ids - synced_recurrences._get_outliers()
            events = self.env['calendar.event']._get_records_to_sync(calendar, full_sync=full_sync)
            (events - synced_events).with_context(send_updates=send_updates)._sync_odoo2google(calendar_service)
            if bool(events | synced_events) or bool(recurrences | synced_recurrences):
                need_refresh = True

        return need_refresh

    def _sync_google_calendar_filter_remote_events(self, google_events):
        """Filter out events coming from google which should not be synced into odoo."""
        # Birthday events appear in a separate virtual calendar in the UI of google calendar which can be confusing.
        # They require special handling and are not very useful in business flows so they are ignored for now.
        return google_events.filter(lambda google_event: google_event.eventType != 'birthday')

    def _sync_single_event(self, calendar_service: GoogleCalendarService, odoo_event, event_id):
        self.ensure_one()
        results = self._sync_request(calendar_service, event_id)
        if not results or not results.get('events'):
            return False
        event, default_reminders, full_sync = results.values()
        # Google -> Odoo
        send_updates = not full_sync
        event.clear_type_ambiguity(self.env)
        synced_events = self.env['calendar.event']._sync_google2odoo(event, default_reminders=default_reminders)
        # Odoo -> Google
        odoo_event.with_context(send_updates=send_updates)._sync_odoo2google(calendar_service)
        return bool(odoo_event | synced_events)

    def _sync_request(self, calendar_service, event_id=None, calendar=None):
        if self._get_google_sync_status() != "sync_active":
            return False
        # don't attempt to sync when another sync is already in progress, as we wouldn't be
        # able to commit the transaction anyway (row is locked)
        self.ensure_one()
        try:
            self.lock_for_update(allow_referencing=True)
        except LockError:
            _logger.info("skipping calendar sync, locked user %s", self.login)
            return False

        full_sync = not bool(calendar.google_sync_token)
        with google_calendar_token(self) as token:
            try:
                if not event_id:
                    events, next_sync_token, default_reminders = calendar_service.get_events(calendar.google_sync_token, token=token, calendar=calendar)
                else:
                    events, next_sync_token, default_reminders = calendar_service.get_events(sync_token=token, token=token, event_id=event_id, calendar=calendar)
            except InvalidSyncToken:
                events, next_sync_token, default_reminders = calendar_service.get_events(token=token, calendar=calendar)
                full_sync = True
        if next_sync_token:
            calendar.google_sync_token = next_sync_token
        return {
            'events': events,
            'default_reminders': default_reminders,
            'full_sync': full_sync,
        }

    @api.model
    def _sync_all_google_calendar(self):
        """ Cron job """
        domain = [('google_calendar_rtoken', '!=', False), ('google_synchronization_stopped', '=', False)]
        # google_calendar_token_validity is not stored on res.users
        if not self:
            users = self.env['res.users'].sudo().search(domain).sorted('google_calendar_token_validity')
        else:
            users = self.filtered_domain(domain).sorted('google_calendar_token_validity')
        google = GoogleCalendarService(self.env['google.service'])
        for user in users:
            _logger.info("Calendar Synchro - Starting synchronization for %s", user)
            try:
                user.with_user(user).sudo()._sync_google_calendar(google)
                self.env.cr.commit()
            except Exception as e:
                _logger.exception("[%s] Calendar Synchro - Exception : %s!", user, exception_to_unicode(e))
                self.env.cr.rollback()

    def is_google_calendar_synced(self):
        """ True if Google Calendar settings are filled (Client ID / Secret) and user calendar is synced
        meaning we can make API calls, false otherwise."""
        self.ensure_one()
        return self.sudo().google_calendar_token and self._get_google_sync_status() == 'sync_active'

    def stop_google_synchronization(self):
        self.ensure_one()
        self.sudo().google_synchronization_stopped = True
        self.sudo().res_users_settings_id._set_google_calendar_email(False)

    def restart_google_synchronization(self):
        self.ensure_one()
        self.sudo().google_synchronization_stopped = False
        self.sudo().google_synchronization_needs_reset = False
        self.env['calendar.calendar']._restart_google_sync()
        self.env['calendar.recurrence']._restart_google_sync()
        self.env['calendar.event']._restart_google_sync()

    def prepare_for_google_calendar_sync(self):
        self.sudo().google_synchronization_needs_reset = True

    def reset_google_sync_records(self):
        self.env['calendar.recurrence']._restart_google_sync()
        self.env['calendar.event']._restart_google_sync()

    def unpause_google_synchronization(self):
        self.env['ir.config_parameter'].sudo().set_bool("google_calendar_sync_paused", False)

    def pause_google_synchronization(self):
        self.env['ir.config_parameter'].sudo().set_bool("google_calendar_sync_paused", True)

    @api.model
    def _has_setup_credentials(self):
        """ Checks if both Client ID and Client Secret are defined in the database. """
        ICP_sudo = self.env['ir.config_parameter'].sudo()
        client_id = self.env['google.service']._get_client_id('calendar')
        client_secret = google_service._get_client_secret(ICP_sudo, 'calendar')
        return bool(client_id and client_secret)

    @api.model
    def check_calendar_credentials(self):
        res = super().check_calendar_credentials()
        res['google_calendar'] = self._has_setup_credentials()
        return res

    def get_calendar_email(self):
        if self.res_users_settings_id.sudo().google_calendar_email:
            return self.res_users_settings_id.sudo().google_calendar_email
        else:
            return super().get_calendar_email()

    def check_synchronization_status(self):
        res = super().check_synchronization_status()
        credentials_status = self.check_calendar_credentials()
        sync_status = 'missing_credentials'
        if credentials_status.get('google_calendar'):
            sync_status = self._get_google_sync_status()
            if sync_status == 'sync_active' and not self.sudo().google_calendar_rtoken:
                sync_status = 'sync_stopped'
        res['google_calendar'] = sync_status
        return res

    def _has_any_active_synchronization(self):
        """
        Check if synchronization is active for Google Calendar.
        This function retrieves the synchronization status from the user's environment
        and checks if the Google Calendar synchronization is active.

        :return: Action to delete the event
        """
        sync_status = self.check_synchronization_status()
        res = super()._has_any_active_synchronization()
        if sync_status.get('google_calendar') == 'sync_active':
            return True
        return res
