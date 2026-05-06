from odoo import models
from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_OPEN_STATES


class PdpFlowHandler(models.AbstractModel):
    _name = 'l10n.fr.pdp.reports.flow.handler'
    _description = 'PDP Flow Handler'

    def _cron_update_and_send_flows(self):
        companies = self.env['res.company'].search([
            ('l10n_fr_f10_enable_reporting', '=', True),
        ])
        for company in companies:
            _logger.info('Running PDP flow handler cron for company %s', company.id)
            try:
                self.sudo().with_company(company)._cron_process_company()
            except Exception:
                _logger.exception('Failed to handle PDP flows for company %s', company.id)

    def _cron_process_company(self):
        # TODO check for sent & cancelled
        open_flows = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.env.company.id),
            ('state', 'in', FLOW_OPEN_STATES),
        ])
