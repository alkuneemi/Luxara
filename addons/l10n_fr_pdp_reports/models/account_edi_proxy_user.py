import uuid

from odoo import _, models
from odoo.exceptions import UserError

DEMO_ENDPOINTS = {  # pdp reports specific endpoints not already mocked by l10n_fr_pdp demo utils
    '/api/pdp/1/participant_status': lambda params: {},
    '/api/pdp/1/send_document': lambda params: {
        'ppf_messages': [{'message_uuid': f'demo_{uuid.uuid4()}'} for _d in params['documents']]
    },
    '/api/pdp/1/pdp_state': lambda params: {},
}


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _call_peppol_proxy(self, endpoint, params=None):
        if self.env.company._get_peppol_edi_mode() == 'demo' and endpoint in DEMO_ENDPOINTS:
            self.ensure_one()
            if self.proxy_type != 'pdp':
                raise UserError(_('EDI user should be of type PDP'))
            return DEMO_ENDPOINTS[endpoint](params)
        else:
            return super()._call_peppol_proxy(endpoint, params)
