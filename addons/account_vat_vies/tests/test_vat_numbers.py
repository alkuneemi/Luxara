from odoo.tests.common import TransactionCase, tagged
from odoo._monkeypatches.stdnum import new_get_soap_client
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from unittest.mock import patch

import stdnum.eu.vat
from lxml import etree
from zeep import Client, Transport
from zeep.wsdl import Document


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestStructure(TransactionCase):
    @classmethod
    def setUpClass(cls):
        def _check_vies_iap(record):
            return "valid" if record.vat == 'BE0477472701' else "unassigned"

        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = False
        cls._check_vies_iap = _check_vies_iap

    @mute_logger('odoo.addons.account.models.partner')
    def test_missing_company_country(self):
        company = self.env['res.company'].create({
            'name': 'Test Company',
            'country_id': False,
            'vat_check_vies': True,
        })
        partner = self.env['res.partner'].create({
            'name': 'Customer BE',
            'country_id': self.env.ref('base.be').id,
            'vat': 'DE123456788',
            'company_id': company.id,
        })
        valid = partner._get_vat_required_valid(company=company)
        self.assertEqual(valid, True)
        partner.vat = False
        invalid = partner._get_vat_required_valid(company=company)
        self.assertEqual(invalid, False)

    @mute_logger('odoo.addons.account.models.partner')
    def test_parent_validation(self):
        """Test the validation with company and contact"""

        # set an invalid vat number
        self.env.user.company_id.vat_check_vies = False
        company = self.env["res.partner"].create({
            "name": "World Company",
            "country_id": self.env.ref("base.be").id,
            "vat": "ATU12345675",
        })

        # reactivate it and correct the vat number
        with patch('odoo.addons.account_vat_vies.models.res_partner.ResPartner._check_vies_iap', TestStructure._check_vies_iap):
            self.env.user.company_id.vat_check_vies = True
            with self.assertRaises(ValidationError):
                company.vat = "BE0987654321"  # VIES refused, don't fallback on other check
            company.vat = "BE0477472701"
            self.assertEqual(company.vies_valid, True)

    def test_soap_client_for_vies_loads(self):
        # Test of stdnum get_soap_client monkeypatch. This test is mostly to
        # see that no unexpected import errors are thrown and not caught.
        with patch.object(Document, '_get_xml_document', return_value=etree.Element("root")), \
                patch.object(Client, 'service', return_value=None):
            doc = Document(location=None, transport=Transport())
            new_get_soap_client(doc, 30)

    def test_no_vies_revalidation_when_creating_company_from_contact(self):
        # Test that we don't revalidate the VAT when create a company from a contact where it's already validated
        self.env.user.company_id.vat_check_vies = True
        with patch('odoo.addons.account_vat_vies.models.res_partner.ResPartner._check_vies_iap', TestStructure._check_vies_iap):
            partner = self.env["res.partner"].create({
                'name': 'Dummy Partner',
                'vat': 'BE0477472701',
                'country_id': self.env.ref("base.be").id,
            })
            self.assertEqual(partner.vies_valid, True)

        with patch('odoo.addons.account_vat_vies.models.res_partner.ResPartner._check_vies_iap',
                   side_effect=Exception('should not call _check_vies_iap()')):
            partner._create_parent_from_name('My Company')
            self.assertEqual(partner.vies_valid, True)
            self.assertEqual(partner.parent_id.name, 'My Company')
            self.assertEqual(partner.parent_id.vies_valid, True)


@tagged('-standard', 'external')
class TestStructureVIES(TestStructure):
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.vat_check_vies = True
        cls._vies_check_func = stdnum.eu.vat.check_vies
