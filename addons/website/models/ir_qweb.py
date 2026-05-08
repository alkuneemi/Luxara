# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import json

from collections import OrderedDict
from markupsafe import Markup, escape_silent
import logging

from lxml import etree
from odoo import models
from odoo.http import request
from odoo.tools import lazy
from odoo.addons.base.models.ir_qweb import indent_code
from odoo.addons.website.models import ir_http
from odoo.addons.website.tools import add_form_signature
from odoo.exceptions import AccessError
from odoo.fields import Domain

_logger = logging.getLogger(__name__)

re_background_image = re.compile(r"(background-image\s*:\s*url\(\s*['\"]?\s*)([^)'\"]+)")


class IrQweb(models.AbstractModel):
    """ IrQweb object for rendering stuff in the website context """

    _inherit = 'ir.qweb'

    URL_ATTRS = {
        'form': 'action',
        'a': 'href',
        'link': 'href',
        'script': 'src',
        'img': 'src',
    }

    def _compile_root(self, element, compile_context):
        # Removes the attributes used by the "/website/snippet/filter_templates"
        # controller and used only to be filtered without using irQweb rendering
        if not self._is_static_node(element, compile_context):
            for data_filter in [
                    'data-number-of-elements', 'data-number-of-elements-sm',
                    'data-number-of-elements-fetch', 'data-row-per-slide',
                    'data-arrow-position', 'data-extra-classes',
                    'data-extra-snippet-classes', 'data-container-classes',
                    'data-content-classes', 'data-column-classes', 'data-thumb',
                ]:
                element.attrib.pop(data_filter, None)
        return super()._compile_root(element, compile_context)

    def _get_template(self, template):
        element, document, ref = super()._get_template(template)
        if self.env.context.get('website_id'):
            add_form_signature(element, self.sudo().env)
        return element, document, ref

    # assume cache will be invalidated by third party on write to ir.ui.view
    def _get_template_cache_keys(self):
        """ Return the list of context keys to use for caching ``_compile``. """
        return super()._get_template_cache_keys() + ['website_id', 'cookies_allowed']

    def _prepare_frontend_environment(self, values):
        """ Update the values and context with website specific value
            (required to render website layout template)
        """
        irQweb = super()._prepare_frontend_environment(values)

        current_website = request.website
        editable = irQweb.env.user.has_group('website.group_website_designer')
        has_group_restricted_editor = irQweb.env.user.has_group('website.group_website_restricted_editor')
        if not editable and has_group_restricted_editor and 'main_object' in values:
            try:
                main_object = values['main_object'].with_user(irQweb.env.user.id)
                current_website._check_user_can_modify(main_object)
                editable = True
            except AccessError:
                pass
        translatable = has_group_restricted_editor and irQweb.env.context.get('lang') != irQweb.env['ir.http']._get_default_lang().code
        editable = editable and not translatable

        if has_group_restricted_editor and irQweb.env.user.has_group('website.group_multi_website'):
            values['multi_website_websites_current'] = lazy(lambda: current_website.name)
            values['multi_website_websites'] = lazy(lambda: [
                {'website_id': website.id, 'name': website.name, 'domain': website.domain}
                for website in current_website.search([('id', '!=', current_website.id)])
            ])

            cur_company = irQweb.env.company
            values['multi_website_companies_current'] = lazy(lambda: {'company_id': cur_company.id, 'name': cur_company.name})
            values['multi_website_companies'] = lazy(lambda: [
                {'company_id': comp.id, 'name': comp.name}
                for comp in irQweb.env.user.company_ids if comp != cur_company
            ])

        # update values

        values.update(dict(
            website=current_website,
            is_view_active=lazy(lambda: current_website.is_view_active),
            res_company=lazy(current_website.company_id.sudo),
            translatable=translatable,
            editable=editable,
        ))

        if editable:
            # form editable object, add the backend configuration link
            if 'main_object' in values and has_group_restricted_editor:
                func = getattr(values['main_object'], 'get_backend_menu_id', False)
                values['backend_menu_id'] = lazy(lambda: func and func() or irQweb.env['ir.model.data']._xmlid_to_res_id('website.menu_website_configuration'))

        # update options

        irQweb = irQweb.with_context(website_id=current_website.id)
        if 'inherit_branding' not in irQweb.env.context and not self.env.context.get('rendering_bundle'):
            if editable:
                # in edit mode add branding on ir.ui.view tag nodes
                irQweb = irQweb.with_context(inherit_branding=True)
            elif has_group_restricted_editor:
                # will add the branding on fields (into values)
                irQweb = irQweb.with_context(inherit_branding_auto=True)

        # Avoid cache inconsistencies: if the cookies have been accepted, the
        # DOM structure should reflect it after a reload and not be stuck in its
        # previous state (see the part related to cookies in
        # `_post_processing_att`).
        is_allowed_optional_cookies = request.env['ir.http']._is_allowed_cookie('optional')
        irQweb = irQweb.with_context(cookies_allowed=is_allowed_optional_cookies)

        return irQweb

    def _compile_directive_dynamic_filter_snippet(self, el, compile_context, indent):
        args = el.attrib.pop('t-dynamic-filter-snippet')
        if  ('snippet_lang' in self.env.context or 'inherit_branding' in self.env.context) and el.tag != 't':
            el.attrib['data-oe-dynamic-filter-snippet'] = args
        parsed_args = json.loads(args)

        content_template_key = parsed_args.get('content_template_key')
        content_extra_data = parsed_args.get('content_extra_data', {})
        wrapper_template_key = parsed_args.get('wrapper_template_key')
        wrapper_extra_data = parsed_args.get('wrapper_extra_data', {})
        filter_id = parsed_args.get('filter_id')
        res_model = parsed_args.get('res_model')
        res_id = parsed_args.get('res_id')
        search_domain = parsed_args.get('search_domain')
        search_domain_extra = parsed_args.get('search_domain_extra')
        limit = parsed_args.get('limit')

        if not filter_id:
            if filter_xmlid := parsed_args.get('filter_xmlid'):
                filter_id = self.env.ref(filter_xmlid).id

        if not content_template_key or not wrapper_template_key or not (filter_id or (res_id and res_model and limit == 1)):
            el.insert(0, etree.Element('t', {'t-call': 'website.s_dynamic_snippet_incomplete'}))
            return []

        with_sample = self.env.context.get('dynamic_filter_snippet_with_sample')

        code = [indent_code(f"values['DYNAMIC_FILTER_SNIPPET_DATA'], values['DYNAMIC_FILTER_SNIPPET_ERROR'] = self._dynamic_filter_snippet_at_runtime({content_template_key!r}, {content_extra_data!r}, {filter_id!r}, {res_model!r}, {res_id!r}, {search_domain!r}, {search_domain_extra!r}, {limit!r}, {with_sample!r}, values.get('main_object', None))", indent)]

        el.insert(0, etree.Element('t', dict({
            't-if': 'DYNAMIC_FILTER_SNIPPET_ERROR',
            't-call': 'website.s_dynamic_snippet_error',
            'error': 'DYNAMIC_FILTER_SNIPPET_ERROR',
        })))

        el.insert(1, etree.Element('t', dict({
            't-else': '',
            't-call': wrapper_template_key,
            'data': 'DYNAMIC_FILTER_SNIPPET_DATA',
            'limit': f"{limit!r}"
        }, **{key: f"{value!r}" for key, value in wrapper_extra_data.items()})))

        return code

    def _dynamic_filter_snippet_at_runtime(self, content_template_key, content_extra_data, filter_id, res_model, res_id, search_domain, search_domain_extra, limit, with_sample, main_object):
        dynamic_filter_sudo = self.env['website.snippet.filter'].sudo().browse(filter_id)
        try:
            return [Markup(item) for item in dynamic_filter_sudo._render(
                template_key=content_template_key,
                limit=limit,
                search_domain=search_domain,
                search_domain_extra=search_domain_extra,
                with_sample=with_sample,
                res_model=res_model,
                res_id=res_id,
                main_object_name=main_object and main_object._name,
                main_object_id=main_object and main_object.id,
                **content_extra_data,
            )], None
        except Exception as error:
            return [], error

    def _directives_eval_order(self):
        directives = super()._directives_eval_order()
        index = directives.index('options')
        directives.insert(index, 'dynamic-filter-snippet')
        return directives

    def _post_processing_att(self, tagName, atts):
        if atts.get('data-no-post-process'):
            return atts

        atts = super()._post_processing_att(tagName, atts)

        website = ir_http.get_request_website()
        if not website and self.env.context.get('website_id'):
            website = self.env['website'].browse(self.env.context['website_id'])
        if website and tagName == 'img' and 'loading' not in atts:
            atts['loading'] = 'lazy'  # default is auto

        if self.env.context.get('inherit_branding') or self.env.context.get('rendering_bundle') or \
           self.env.context.get('edit_translations') or self.env.context.get('debug') or (request and request.session.debug):
            return atts

        if not website:
            return atts

        if website._should_remove_third_party_trackers():
            website._remove_third_party_trackers(tagName, atts, ['domains', 'classes'])

        name = self.URL_ATTRS.get(tagName)
        if request:
            value = atts.get(name) if name else None
            if value not in (None, False, ()):
                atts[name] = self.env['ir.http']._url_for(str(value))

            # Adapt background-image URL in the same way as image src.
            atts = self._adapt_style_background_image(atts, self.env['ir.http']._url_for)

        if not website.cdn_activated:
            return atts

        data_name = f'data-{name}'
        if name and (name in atts or data_name in atts):
            atts = OrderedDict(atts)
            if name in atts and atts[name] not in (False, None, ()):
                atts[name] = website.get_cdn_url(atts[name])
            if data_name in atts and atts[data_name] not in (False, None, ()):
                atts[data_name] = website.get_cdn_url(atts[data_name])
        atts = self._adapt_style_background_image(atts, website.get_cdn_url)

        return atts

    def _adapt_style_background_image(self, atts, url_adapter):
        if isinstance(atts.get('style'), str) and 'background-image' in atts['style']:
            atts['style'] = re_background_image.sub(lambda m: '%s%s' % (m[1], url_adapter(m[2])), atts['style'])
        return atts
