# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ph_branch_code = fields.Char(
        string="Branch Code",
        help="Leave blank for individuals to enable automatic first and last name splitting."
             "For corporate Head Offices, input '00000'.",
        compute='_compute_branch_code',
        store=True,
    )
    l10n_ph_first_names = fields.Char(
        "First Names",
        compute='_l10n_ph_compute_split_name',
        inverse='_l10n_ph_inverse_split_name',
    )
    l10n_ph_middle_name = fields.Char(
        "Middle Name",
        compute='_l10n_ph_compute_split_name',
        inverse='_l10n_ph_inverse_split_name',
    )
    l10n_ph_last_name = fields.Char(
        "Last Name",
        compute='_l10n_ph_compute_split_name',
        inverse='_l10n_ph_inverse_split_name',
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_ph_branch_code']

    @api.depends('name', 'l10n_ph_branch_code', 'fiscal_country_codes')
    def _l10n_ph_compute_split_name(self):
        """
        In the Philippines, names contains the following information:
            - One to three+ first names. It is very common to have two.
            - One middle name, the mother's maiden surname.
            - One last name, the father's surname.
        """
        for partner in self:
            if 'PH' not in partner.fiscal_country_codes or partner.l10n_ph_branch_code:
                continue

            first, middle, last = False, False, False
            if partner.name:
                parts = partner.name.split()

                # If only one word, it's just a first name
                if len(parts) == 1:
                    first = parts[0]
                else:
                    # Last word is Last Name, second to last is Middle Name, everything else is first.
                    last = parts.pop()
                    middle = parts.pop() if len(parts) > 1 else False
                    first = " ".join(parts)

            partner.write({
                'l10n_ph_first_names': first,
                'l10n_ph_middle_name': middle,
                'l10n_ph_last_name': last,
            })

    def _l10n_ph_inverse_split_name(self):
        """
        This inverse is here to allow adjusting the manually computed split name, in case the input was not in the
        expected order.
        """
        for partner in self:
            if 'PH' not in partner.fiscal_country_codes or partner.l10n_ph_branch_code:
                continue

            parts = [
                partner.l10n_ph_first_names,
                partner.l10n_ph_middle_name,
                partner.l10n_ph_last_name,
            ]
            partner.name = " ".join(p.strip() for p in parts if p and p.strip()) or partner.name

    @api.depends('vat', 'country_id')
    def _compute_branch_code(self):
        for partner in self:
            branch_code = False
            if partner.country_id.code == 'PH' and partner.vat:
                match = partner._check_vat_ph_re.match(partner.vat)
                branch_code = (match and match.group(1) and match.group(1)[1:]) or branch_code
            partner.l10n_ph_branch_code = branch_code
