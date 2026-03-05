from odoo.addons.microsoft_account.controllers.main import MicrosoftAuth
from odoo.http import request

class MicrosoftCalendarAuth(MicrosoftAuth):

    def _on_microsoft_auth_success(self):
        super()._on_microsoft_auth_success()
        request.env.user.microsoft_synchronization_needs_reset = True
