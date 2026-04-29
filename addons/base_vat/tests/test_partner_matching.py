# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase


class TestPartnerMatching(TransactionCase):

    def test_res_partner_search_swiss_vat_consistency(self):
        """
        Ensure Swiss VAT matching is resilient to formatting (dots, hyphens), casing, and language suffixes (TVA/MWST/IVA).
        """
        initial_partner = self.env['res.partner'].create({
            'name': 'CH Test',
            'country_id': self.ref('base.ch'),
            'vat': 'CHE-123.456.788 TVA',
        })
        self.assertTrue(initial_partner)

        # variants = [
        #     'CHE-123.456.788 TVA', 'CHE-123.456.788 IVA', 'CHE-123.456.788 MWST',
        #     'CHE123456788TVA', 'CHE123456788IVA', 'CHE123456788MWST',
        #     'CHE123456788', 'che123456788tva', 'CHE 123 456 788',
        # ]
        # variants = [
        #     'CHE-123.456.788 TVA',
        #     'CHE123456788TVA',
        #     'CHE123456788', 'che123456788tva', 'CHE 123 456 788',
        # ]
        variants = [
            'CHE-123.456.788 TVA', 'CHE123456788TVA', 'che123456788tva',
        ]
        for vat_to_test in variants:
            variant_partner = self.env['res.partner']._retrieve_partner(vat=vat_to_test)
            self.assertEqual(initial_partner, variant_partner, f"Failed for formatted CH VAT: {vat_to_test}")

        other_partner = self.env['res.partner']._retrieve_partner(vat='CHE123456780TVA')
        self.assertNotEqual(initial_partner, other_partner)
