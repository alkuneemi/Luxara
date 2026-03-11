# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain

from odoo.addons.portal.controllers.thread import PortalWebClientController


class PortalRatingThreadController(PortalWebClientController):
    @classmethod
    def _get_non_empty_message_domain(self):
        return super()._get_non_empty_message_domain() | Domain("rating_value", "!=", False)

    @classmethod
    def _get_fetch_domain(self, thread, **kwargs):
        domain = super()._get_fetch_domain(thread, **kwargs)
        if kwargs.get("rating_value", False) is not False:
            domain &= Domain("rating_value", "=", float(kwargs["rating_value"]))
        return domain
