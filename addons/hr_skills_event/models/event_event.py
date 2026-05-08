# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class EventEvent(models.Model):
    _inherit = 'event.event'

    @api.model_create_multi
    def create(self, vals_list):
        """ When creating an event from the Onsite Courses view, register the current employee as attendee of the event."""
        events = super().create(vals_list)
        if self.env.context.get('is_onsite'):
            for event in events:
                employee = self.env['hr.employee'].search([('id', '=', self.env.context.get('default_employee'))], limit=1)
                partner = employee.work_contact_id if employee else None
                if partner and partner not in event.mapped('registration_ids.partner_id'):
                    event.registration_ids.create({
                        'partner_id': partner.id,
                        'event_id': event.id,
                    })
        return events
