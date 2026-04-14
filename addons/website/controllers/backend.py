# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.webclient import WebClient

def _request_update_context_website_id(env, website_id):
    if not website_id:
        return

    error_msg = env._("You do not have access to that website.")
    try:
        website_id = int(website_id)
    except (TypeError, ValueError):
        raise AccessError(error_msg)

    if website_id not in env['website'].get_all().ids:
        raise AccessError(error_msg)

    if (website_id not in (env.context.get('website_id'), env.context.get('fallback_website_id'))
        and not (
            (user := env.user or env['res.users'].sudo().browse(request.session.uid))
            and user.has_group('website.group_multi_website')
            and user.has_group('website.group_website_restricted_editor')
        )
    ):
        raise AccessError(error_msg)

    request.update_context(website_id=website_id)


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="jsonrpc", auth='user', readonly=True)
    def fetch_dashboard_data(self, website_id):
        Website = request.env['website']
        has_group_system = request.env.user.has_group('base.group_system')
        has_group_designer = request.env.user.has_group('website.group_website_designer')
        dashboard_data = {
            'groups': {
                'system': has_group_system,
                'website_designer': has_group_designer
            },
            'dashboards': {}
        }

        current_website = website_id and Website.browse(website_id) or Website.get_current_website()
        multi_website = request.env.user.has_group('website.group_multi_website')
        websites = multi_website and request.env['website'].search([]) or current_website
        dashboard_data['websites'] = websites.read(['id', 'name'])
        for website in dashboard_data['websites']:
            if website['id'] == current_website.id:
                website['selected'] = True

        if has_group_designer:
            dashboard_data['dashboards']['plausible_share_url'] = current_website._get_plausible_share_url()
        return dashboard_data

    @http.route('/website/iframefallback', type="http", auth='user', website=True, readonly=True)
    def get_iframe_fallback(self):
        return request.render('website.iframefallback')

    @http.route('/website/track_installing_modules', type='jsonrpc', auth='user', readonly=True)
    def website_track_installing_modules(self, selected_features, total_features=None):
        """
        During the website configuration, this route allows to track the
        website features being installed and their dependencies in order to
        show the progress between installed and yet to install features.
        """
        features_not_installed = request.env['website.configurator.feature']\
            .browse(selected_features).module_id.upstream_dependencies(exclude_states=())\
            .filtered(lambda feature: feature.state != 'installed')

        # On the 1st run, the total tallies the targeted, not yet installed
        # features. From then on, the compared to total should not change.
        total_features = total_features or len(features_not_installed)
        features_info = {
            'total': total_features,
            'nbInstalled': total_features - len(features_not_installed)
        }
        return features_info


class WebsiteWebHome(Home):

    @http.route()
    def web_client(self, s_action=None, *, website_id=None, **kw):
        if kw.get('subpath') == 'action-website.website_preview':
            _request_update_context_website_id(self.env, website_id)
        return super().web_client(s_action, **kw)


class WebsiteWebClient(WebClient):

    @http.route()
    def bundle(self, bundle_name, *, website_id=None, **bundle_params):
        _request_update_context_website_id(self.env, website_id)
        return super().bundle(bundle_name, **bundle_params)
