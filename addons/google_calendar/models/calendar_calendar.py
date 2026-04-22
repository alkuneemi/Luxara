import logging

from requests import HTTPError

from odoo import api, fields, models
from odoo.addons.google_calendar.models.google_sync import google_calendar_token, after_commit
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendar
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
from odoo.fields import Domain


_logger = logging.getLogger(__name__)


class CalendarCalendar(models.Model):
    _name = 'calendar.calendar'
    _inherit = ['calendar.calendar', 'google.sync']

    google_sync_token = fields.Char('Sync Token')
    linked_email = fields.Char('Linked Email', readonly=True)
    user_google_email = fields.Char(related='user_id.google_calendar_email')

    @staticmethod
    def _get_google_synced_fields_map():
        return {'name': 'summary'}

    def _google_values(self):
        return {google_field: getattr(self, odoo_field) for odoo_field, google_field in
            self._get_google_synced_fields_map().items()}

    def write(self, vals):
        synced_fields = self._get_google_synced_fields_map().keys() | {'active'}
        if 'need_sync' not in vals and vals.keys() & synced_fields and not self.env.user.google_synchronization_stopped:
            vals['need_sync'] = True

        result = super().write(vals)

        # When the module is installed, we archive records instead of deleting them
        # ondelete=cascade does not trigger on archivation -> we need to make sure to delete/archive related records
        if not vals.get('active', True):
            self.env['calendar.event'].search([
                ('calendar_id', 'in', self.ids),
            ]).unlink()
            self.env['calendar.recurrence'].search([
                ('calendar_id', 'in', self.ids),
            ]).unlink()
            self.env['calendar.calendar.filter'].search([
                ('calendar_id', 'in', self.ids)
            ]).unlink()

        if self.env.user._get_google_sync_status() == "sync_active":
            google_service = GoogleCalendarService(self.env['google.service'])
            for record in self:
                if record.need_sync and record.google_id and record.active and not record.is_readonly:
                    record._google_calendar_patch(google_service)

        return result

    @api.model_create_multi
    def create(self, vals_list):
        user_ids = {v['user_id'] for v in vals_list if v.get('user_id')}
        users_with_sync = self.env['res.users'].browse(user_ids).filtered(
            lambda u: not u.sudo().google_synchronization_stopped)
        users_with_sync_set = set(users_with_sync.ids)

        for vals in vals_list:
            if vals.get('user_id', False) and vals['user_id'] not in users_with_sync_set:
                vals.update({'need_sync': False})
        records = super().create(vals_list)

        google_service = GoogleCalendarService(self.env['google.service'])
        if self.env.user._get_google_sync_status() == "sync_active":
            for record in records:
                if record.user_id == self.env.user and record.need_sync and record.active:
                    record._google_calendar_insert(google_service)
        return records

    def _sync_calendars_google2odoo(self, google_calendars: GoogleCalendar):
        existing = google_calendars.exists(self.env)
        primary = google_calendars.get_primary()
        deleted = google_calendars.get_deleted()
        updated = existing - deleted
        new = google_calendars - updated - primary - deleted

        # Create
        self._create_odoo_calendars(new)
        # Link primary
        if primary:
            primary_odoo = self.browse(primary.odoo_id(self.env))
            primary_odoo.google_id = primary.id
        # Delete
        deleted_odoo = self.browse(deleted.odoo_ids(self.env)).filtered(lambda odoo: not odoo.is_primary)
        if deleted_odoo:
            deleted_odoo.with_context(dont_notify=True).write({'google_id': False})
            deleted_odoo.unlink()
        # Update
        for calendar in updated:
            odoo_record = self.browse(calendar.odoo_id(self.env))
            # Unlike for events, the calendar endpoints do not return an 'updated' timestamp, meaning we can't
            # rely on last write date to determine which update wins in case of a conflict - we have to decide
            # which side is authoritative. In this case -> Odoo
            if not odoo_record.exists() or odoo_record.need_sync:
                # The record must have been edited or deleted in the meantime
                continue

            vals = {'need_sync': False}
            for odoo_field, google_field in self._get_google_synced_fields_map().items():
                pending_value = calendar.google_field
                if pending_value and getattr(odoo_record, odoo_field) != pending_value:
                    vals[odoo_field] = pending_value
            odoo_record.write(vals)

    def _sync_calendars_odoo2google(self, calendar_service):
        if not self or self.env.user._get_google_sync_status() != "sync_active":
            return

        # Do not delete the calendars on the side of Google, we do not want to handle such destructive flows
        # Instead, we just archive it on our side so that it is no longer synchronized.
        records_to_sync = self.filtered(self._active_name) if self._active_name else self
        for calendar in records_to_sync:
            if not calendar.google_id and not calendar.is_primary:
                calendar._google_calendar_insert(calendar_service)
            else:
                calendar._google_calendar_patch(calendar_service)

    def _create_odoo_calendars(self, google_calendars: GoogleCalendar):
        if not google_calendars:
            return
        new_calendars = self.create([dict(self._odoo_values(c), need_sync=False) for c in google_calendars])
        self.env['calendar.calendar.filter'].create([c._filter_values() for c in new_calendars])

    @api.model
    def _odoo_values(self, google_record: GoogleCalendar):
        return {
            'google_id': google_record.id,
            'name': google_record.summary,
            'is_readonly': google_record.accessRole != 'owner',
            'user_id': self.env.user.id,
            'linked_email': self.env.user.google_calendar_email,
        }

    @after_commit
    def _google_calendar_patch(self, calendar_service: GoogleCalendarService):
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                calendar_service.patch_calendar(self, self._google_values(), token=token)
                self.exists().with_context(dont_notify=True).need_sync = False
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    @after_commit
    def _google_calendar_delete(self, calendar_service: GoogleCalendarService):
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                calendar_service.delete_calendar(self, token=token)
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    @after_commit
    def _google_calendar_insert(self, calendar_service: GoogleCalendarService):
        with google_calendar_token(self.env.user.sudo()) as token:
            if not token:
                return
            try:
                response = calendar_service.insert_calendar(self._google_values(), token=token)
                self.with_context(dont_notify=True).write({
                    'google_id': response['id'],
                    'linked_email': self.env.user.google_calendar_email,
                    'need_sync': False,
                })
            except HTTPError as e:
                if e.response.status_code in (400, 403):
                    self._google_error_handling(e)

    def _google_error_handling(self, http_error):
        response = http_error.response.json()
        reason = "Google gave the following explanation: %s" % response['error'].get('message')
        if not self.exists():
            _logger.error("Error while syncing calendar. It does not exists anymore in the database. %s", reason)
        else:
            _logger.error("Error while syncing calendar. %s", reason)

    def _get_sync_domain(self):
        return Domain([('user_id', '=', self.env.user.id)])

    @api.model
    def _restart_google_sync(self):
        calendars = self.env['calendar.calendar'].search(self._get_sync_domain())
        calendars.write({'need_sync': True})
        # When synchronized, we do not delete calendars in Google. Instead of deleting them in Odoo, we archive
        # them so that we know not to sync again. On a reset, we remove them so that they can be synced again.
        deleted = calendars.filtered(lambda c: not c.active)
        deleted.write({'google_id': False})  # unlink instead of archive
        deleted.unlink()
