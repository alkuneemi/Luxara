# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import fields, models, api, _
from odoo.tools import file_open


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_closing_sequence_id = fields.Many2one('ir.sequence', 'Sequence to use to build sale closings', readonly=True)
    ape = fields.Char(string='APE')
    is_france_country = fields.Boolean(
        compute="_compute_is_france_country",
        string="Is Part of DOM-TOM",
    )

    @api.depends('country_code')
    def _compute_is_france_country(self):
        for company in self:
            company.is_france_country = company.country_code in self._get_france_country_codes()

    @api.model
    def _get_france_country_codes(self):
        """Returns every country code that can be used to represent France
        """
        return ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF', 'BL', 'PM', 'YT', 'WF']  # These codes correspond to France and DOM-TOM.

    def _is_accounting_unalterable(self):
        if not self.vat and not self.country_id:
            return False
        return self.country_id and self.country_id.code in self._get_france_country_codes()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            #when creating a new french company, create the securisation sequence as well
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_closing_sequence_id']
                company._create_secure_sequence(sequence_fields)
        self.apply_worldline_branding()
        return companies

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_closing_sequence_id']
                company._create_secure_sequence(sequence_fields)
        self.apply_worldline_branding()
        return res

    @api.model
    def load_image_base64(self, module_name, *relative_parts):
        if not module_name or not relative_parts:
            return False

        image_path = '/'.join((module_name, *relative_parts))
        try:
            with file_open(
                image_path,
                'rb',
                filter_ext=('.png'),
            ) as image_file:
                return base64.b64encode(image_file.read()).decode()
        except (FileNotFoundError, ValueError):
            return False

    @api.model
    def apply_worldline_branding(self):
        if 'payment.provider' not in self.env.registry:
            return True
        fr_image = self.load_image_base64('l10n_fr', 'static', 'description', 'worldline_cawl.png')
        default_image = self.load_image_base64(
            'payment_worldline', 'static', 'description', 'icon.png'
        )
        for compagny in self:
            main_company = compagny.env['res.company']._get_main_company()

            # If the provider is not installed we overwrite the XML record
            provider = compagny.env.ref('payment.payment_provider_worldline', raise_if_not_found=False)
            if provider and provider.module_state != 'installed':
                if compagny != main_company:
                    continue
                is_fr_company = main_company.is_france_country
                values = {'name': 'CAWL (Worldline)' if is_fr_company else 'Worldline'}
                if is_fr_company and fr_image:
                    values['image_128'] = fr_image
                elif not is_fr_company and default_image:
                    values['image_128'] = default_image
                provider.sudo().write(values)
                continue

            # If the provider is installed we update the provider record
            providers = compagny.env['payment.provider'].sudo().search([('code', '=', 'worldline')])
            for provider in providers:
                is_fr_company = provider.company_id.is_france_country
                values = {'name': 'CAWL (Worldline)' if is_fr_company else 'Worldline'}
                if is_fr_company and fr_image:
                    values['image_128'] = fr_image
                elif not is_fr_company and default_image:
                    values['image_128'] = default_image
                provider.write(values)
        return True

    @api.model
    def reset_worldline_branding(self):
        if 'payment.provider' not in self.env.registry:
            return True
        default_image = self.load_image_base64('payment_worldline', 'static', 'description', 'icon.png')
        for compagny in self:
            main_company = compagny.env['res.company']._get_main_company()
            values = {'name': 'Worldline'}
            if default_image:
                values['image_128'] = default_image

            # Change the provider XMD ID (in case the provider is not installed)
            provider = compagny.env.ref('payment.payment_provider_worldline', raise_if_not_found=False)
            if provider and provider.module_state != 'installed':
                if compagny != main_company:
                    continue
                provider.sudo().write(values)
                continue

            # Change every record (in case the provider is installed)
            providers = compagny.env['payment.provider'].sudo().search([('code', '=', 'worldline')])
            if not providers:
                continue
            providers.write(values)
        return True

    def _create_secure_sequence(self, sequence_fields):
        """This function creates a no_gap sequence on each company in self that will ensure
        a unique number is given to all posted account.move in such a way that we can always
        find the previous move of a journal entry on a specific journal.
        """
        for company in self:
            vals_write = {}
            for seq_field in sequence_fields:
                if not company[seq_field]:
                    vals = {
                        'name': _('Securisation of %(field)s - %(company)s', field=seq_field, company=company.name),
                        'code': 'FRSECURE%s-%s' % (company.id, seq_field),
                        'implementation': 'no_gap',
                        'prefix': '',
                        'suffix': '',
                        'padding': 0,
                        'company_id': company.id}
                    seq = self.env['ir.sequence'].create(vals)
                    vals_write[seq_field] = seq.id
            if vals_write:
                company.write(vals_write)
