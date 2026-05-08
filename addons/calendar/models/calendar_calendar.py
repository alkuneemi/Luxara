from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class CalendarCalendar(models.Model):
    _name = 'calendar.calendar'
    _description = 'Calendar'

    _unique_primary_per_user = models.UniqueIndex('(user_id) WHERE is_primary = TRUE')

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)

        if 'calendar_default_privacy' not in defaults and 'calendar_default_privacy' in fields:
            user_id = defaults.get('user_id')
            if not user_id:
                return defaults

            user = self.env['res.users'].browse(user_id)
            privacy = user.sudo().res_users_settings_id.calendar_default_privacy
            privacy_fallback = self.env['ir.config_parameter'].sudo().get_str('calendar.default_privacy', 'public')
            defaults['calendar_default_privacy'] = privacy or privacy_fallback

        return defaults

    color = fields.Integer(string='Color', default=1)
    event_ids = fields.One2many('calendar.event', 'calendar_id', "Events")
    recurrence_ids = fields.One2many('calendar.recurrence', 'calendar_id', "Recurrences")
    is_primary = fields.Boolean('Primary Calendar', readonly=True)
    is_readonly = fields.Boolean('Readonly Calendar', readonly=True)
    name = fields.Char('Name', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True,
                              ondelete='cascade', index=True, default=lambda self: self.env.user)

    calendar_default_privacy = fields.Selection(
        [('public', 'Public by default'),
         ('private', 'Private by default'),
         ('confidential', 'Internal users only')],
        default='private',
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_primary(self):
        if any(calendar.is_primary for calendar in self):
            raise UserError(_("A primary calendar cannot be deleted."))

    def write(self, vals):
        """ Forbid the calendar default privacy update from different users for keeping private events secured. """
        if 'calendar_default_privacy' in vals:
            if any(calendar.user_id != self.env.user for calendar in self):
                raise AccessError(
                    _("You are not allowed to change the calendar default privacy of another user due to privacy constraints."))
        return super().write(vals)

    def _filter_values(self):
        return {
            'user_id': self.user_id.id,
            'calendar_id': self.id,
            'active': True,
            'is_checked': True,
        }
