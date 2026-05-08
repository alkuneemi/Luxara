from odoo.addons.google_account.controllers.main import GoogleAuth
from odoo.http import request


class GoogleCalendarAuth(GoogleAuth):

    def _on_google_auth_success(self):
        super()._on_google_auth_success()
        request.env.user.sudo().google_synchronization_needs_reset = True
