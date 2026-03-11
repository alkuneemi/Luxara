from odoo import fields, models


class CalendarAttendeeInviteWizard(models.TransientModel):
    _name = 'calendar.attendee.invite.wizard'
    _description = 'Calendar Attendee Invite Wizard'

    calendar_attendee_ids = fields.Many2many('calendar.attendee')
    is_confirmation_required = fields.Boolean()

    def action_confirm(self):
        self.calendar_attendee_ids.event_id._action_confirm()

    def action_send(self):
        self.calendar_attendee_ids._send_invitation_emails()

    def action_send_and_confirm(self):
        self.action_send()
        self.action_confirm()
