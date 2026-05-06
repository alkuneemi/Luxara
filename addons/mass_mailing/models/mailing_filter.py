# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.exceptions import AccessError, ValidationError


class MailingFilter(models.Model):
    """ This model stores mass mailing or marketing campaign domain as filters
    (quite similar to 'ir.filters' but dedicated to mailing apps). Frequently
    used domains can be reused easily.
    In the UI, this model is displayed as dynamic list."""
    _name = 'mailing.filter'
    _description = 'Mailing Favorite Filter'
    _order = 'create_date DESC'

    # override create_uid field to display default value while creating filter from 'Configuration' menus
    create_uid = fields.Many2one('res.users', 'Saved by', index=True, readonly=True, default=lambda self: self.env.user)
    name = fields.Char(string='Filter Name', required=True)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color', default=0)
    mailing_domain = fields.Char(string='Filter Domain', required=True)
    mailing_model_id = fields.Many2one('ir.model', string='Recipients Model', required=True, ondelete='cascade')
    mailing_model_name = fields.Char(string='Recipients Model Name', related='mailing_model_id.model')
    mailing_count = fields.Integer(string="Number of Mailing", compute="_compute_mailing_count")

    @api.constrains('mailing_domain', 'mailing_model_id')
    def _check_mailing_domain(self):
        """ Check that if the mailing domain is set, it is a valid one """
        for mailing_filter in self:
            if mailing_filter.mailing_domain != "[]":
                try:
                    self.env[mailing_filter.mailing_model_id.model].search_count(literal_eval(mailing_filter.mailing_domain))
                except:
                    raise ValidationError(
                        _("The filter domain is not valid for this recipients.")
                    )

    def _compute_mailing_count(self):
        data = {}
        if self.ids:
            self.env.cr.execute('''
                SELECT mailing_filter_id, count(*)
                FROM mail_mass_mailing_filter_rel
                WHERE mailing_filter_id IN %s
                GROUP BY mailing_filter_id''', (tuple(self.ids),))
            data = dict(self.env.cr.fetchall())
        for mailing_filter in self:
            mailing_filter.mailing_count = data.get(mailing_filter._origin.id, 0)

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_view_recipients(self):
        self.ensure_one()
        target_model = self.mailing_model_id
        action = {
            'type': 'ir.actions.act_window',
            'name': target_model.name,
            'res_model': target_model.model,
            'views': [(False, 'list'), (False, 'form')],
            'target': 'current',
            'domain': literal_eval(self.mailing_domain),
            'context': {**self.env.context, 'create': False},
        }
        return action

    def action_view_mailings(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')
        action['domain'] = [('mailing_filter_ids', 'in', self.ids)]
        action['context'] = {'default_mailing_type': 'mail', 'default_mailing_filter_ids': self.ids}
        return action

    def action_send_mailing(self):
        """Open the mailing form view, with the current model & domain set as the mailing model & mailing domain.
        respectively"""
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')

        action.update({
            'context': {
                **self.env.context,
                'default_mailing_filter_ids': self.ids,
                'default_mailing_type': 'mail',
                'default_mailing_model_id': self.mailing_model_id.id,
            },
            'target': 'current',
            'views': [(False, 'form')],
        })

        return action

    @api.model
    def get_dynamic_list_templates_info(self):
        today = Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        date_to = (today + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        return {
            'start_from_scratch': {
                'title': _('Start from Scratch'),
                'description': _('Define your own rules'),
                'icon': '/mass_mailing/static/img/strike.svg',
                'function': 'get_mailing_list_template_values',
                'domain': repr([])
            },
            'recent_sign_ups': {
                'title': _('Recent Sign-ups'),
                'description': _('Mailing Contacts added during the last 30 days'),
                'icon': '/mass_mailing/static/img/wifi.svg',
                'function': 'get_mailing_list_template_values',
                'domain': repr([("create_date", ">=", "today -30d"), ("create_date", "<", "today +1d")])
            },
            'super_fans': {
                'title': _('Super Fans'),
                'description': _('Mailing Contacts with a 100%% open rate over the last 30 days '),
                'icon': '/mass_mailing/static/img/rocket.svg',
                'function': 'get_mailing_list_template_values',
                'domain': repr(["&", ("opened_ratio", "=", 100),
                    ("trace_ids", "any", ["&", ("open_datetime", ">=", date_from), ("open_datetime", "<", date_to)])
                ])
            },
            'recent_visitors': {
                'title': _('Recent Visitors'),
                'description': _('Mailing Contacts that have clicked in a mailing in the last 7 days'),
                'icon': '/mass_mailing/static/img/magnifying_glass.svg',
                'function': 'get_mailing_list_template_values',
                'domain': repr([("trace_ids", "any", ["&",
                    ("links_click_datetime", ">=", (today - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")),
                    ("links_click_datetime", "<", today.strftime("%Y-%m-%d %H:%M:%S"))])
                ])
            },
            'engaged_mailing_contacts': {
                'title': _('Engaged Mailing Contacts'),
                'description': _('Mailing Contacts who have replied, clicked or opened a mailing the last 30 days'),
                'icon': '/mass_mailing/static/img/sales.svg',
                'function': 'get_mailing_list_template_values',
                'domain': repr(["|", "|",
                    ("trace_ids", "any", ["&",
                        ("links_click_datetime", ">=", date_from),
                        ("links_click_datetime", "<", date_to)
                    ]),
                    ("trace_ids", "any", ["&",
                        ("open_datetime", ">=", date_from),
                        ("open_datetime", "<", date_to)
                    ]),
                    ("trace_ids", "any", ["&",
                        ("reply_datetime", ">=", date_from),
                        ("reply_datetime", "<", date_to)
                    ]),
                ])
            },
            'disengaged_mailing_contacts': {
                'title': _('Disengaged Mailing Contacts'),
                'description': _('Mailing Contacts who have NOT replied, clicked or opened a mailing the last 30 days'),
                'icon': '/mass_mailing/static/img/sales_down.svg',
                'function': 'get_mailing_list_template_values',
                'domain': repr(["!", "|", "|",
                    ("trace_ids", "any", ["&",
                        ("links_click_datetime", ">=", date_from),
                        ("links_click_datetime", "<", date_to)
                    ]),
                    ("trace_ids", "any", ["&",
                        ("open_datetime", ">=", date_from),
                        ("open_datetime", "<", date_to)
                    ]),
                    ("trace_ids", "any", ["&",
                        ("reply_datetime", ">=", date_from),
                        ("reply_datetime", "<", date_to)
                    ]),
                ])
            },
        }

    def get_mailing_list_template_values(self, domain, title):
        if not self.env.su and not self.env.user.has_group('mass_mailing.group_mass_mailing_user'):
            raise AccessError(_('To use this feature you should be an administrator or belong to the mass mailing group.'))

        mailing_contact_model_id = self.env['ir.model']._get_id('mailing.contact')
        ctx = dict(
            **self.env.context,
            default_name=title,
            default_mailing_model_id=mailing_contact_model_id)
        if domain:
            ctx['default_mailing_domain'] = literal_eval(domain)
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.mailing_filter_action")
        action['views'] = [(False, 'form')]
        action['target'] = 'new'
        action['context'] = ctx

        return action
