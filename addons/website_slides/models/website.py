# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class Website(models.Model):
    _inherit = "website"

    website_slide_google_app_key = fields.Char('Google Doc Key', groups='base.group_system')

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Courses'), self.env['ir.http']._url_for('/slides'), 'website_slides'))
        return suggested_controllers

    def get_cta_candidates(self, website_purpose, website_type):
        candidates = super().get_cta_candidates(website_purpose, website_type)
        if website_purpose == 'sell_more' and website_type == 'elearning':
            candidates.append((60, {
                'cta_btn_text': _('Browse Courses'),
                'cta_btn_href': '/courses',
            }))
        return candidates

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['slides', 'slide_channel', 'all']:
            result.append(self.env['slide.channel']._search_get_detail(self, order, options))
        if search_type == 'slides':
            result.append(self.env['slide.slide']._search_get_detail(self, order, options))
        return result
