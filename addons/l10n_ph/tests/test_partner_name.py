# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPartnerName(TestPhCommon):

    def test_name_computation(self):
        partner = self.env['res.partner'].create({"name": "Maria Clara Santos Reyes"})

        self.assertEqual(partner.l10n_ph_first_names, "Maria Clara")
        self.assertEqual(partner.l10n_ph_middle_name, "Santos")
        self.assertEqual(partner.l10n_ph_last_name, "Reyes")

    def test_name_inverse(self):
        partner = self.env['res.partner'].create({"name": "Reyes Maria Clara Santos"})

        partner.write({
            "l10n_ph_first_names": "Maria Clara",
            "l10n_ph_middle_name": "Santos",
            "l10n_ph_last_name": "Reyes",
        })

        self.assertEqual(partner.name, "Maria Clara Santos Reyes")

    def test_name_single_word(self):
        partner = self.env['res.partner'].create({"name": "Juan"})

        self.assertEqual(partner.l10n_ph_first_names, "Juan")
        self.assertFalse(partner.l10n_ph_middle_name)
        self.assertFalse(partner.l10n_ph_last_name)
