# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged


@tagged('at_install', '-post_install')
class TestMailingFilter(MassMailCommon):
    """Unit tests for the `mailing.filter` (Dynamic List) model"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_compute_mailig_count(self):
        # Prepapre
        res_partner_model_id = self.env['ir.model']._get('res.partner').id
        filter_1, filter_2 = self.env['mailing.filter'].create([
            {
                'name': 'LLN City',
                'mailing_domain': [('city', 'ilike', 'LLN')],
                'mailing_model_id': res_partner_model_id,
            },
            {
                'name': 'Email based',
                'mailing_domain': [('email', 'ilike', 'info@odoo.com')],
                'mailing_model_id': res_partner_model_id,
            }
        ])
        self.env['mailing.mailing'].create([
            {
                'subject': 'First subject',
                'mailing_model_id': res_partner_model_id,
                'mailing_filter_ids': filter_1 | filter_2
            },
            {
                'subject': 'Second subject',
                'mailing_model_id': res_partner_model_id,
                'mailing_filter_ids': filter_1
            }
        ])
        # Execute & assert
        self.assertEqual(2, filter_1.mailing_count)
        self.assertEqual(1, filter_2.mailing_count)

    def test_action_view_recipients(self):
        # Prepare
        res_partner_model = self.env['ir.model']._get('res.partner')
        self.env['res.partner'].create([
            {
                'name': 'Contact one',
                'city': 'Brussels'
            }
        ])
        domain_1 = [('city', 'ilike', 'Brussels')]
        filter_1 = self.env['mailing.filter'].create([
            {
                'name': 'Brussels contacts',
                'mailing_domain': domain_1,
                'mailing_model_id': res_partner_model.id
            }
        ])
        # Execute
        action_1 = filter_1.action_view_recipients()
        # Assert
        self.assertFalse(action_1['context']['create'])
        self.assertEqual(res_partner_model.model, action_1['res_model'])
        self.assertEqual(domain_1, action_1['domain'])

    def test_action_send_mailing(self):
        # Prepare
        filter_1 = self.env['mailing.filter'].create([
            {
                'name': 'Brussels contacts',
                'mailing_domain': [('city', 'ilike', 'Brussels')],
                'mailing_model_id': self.env['ir.model']._get('res.partner').id
            }
        ])
        # Execute
        action = filter_1.action_send_mailing()
        # Assert
        self.assertEqual('mailing.mailing', action['res_model'])
        self.assertEqual('mail', action['context']['default_mailing_type'])
        self.assertEqual(filter_1.mailing_model_id.id, action['context']['default_mailing_model_id'])
        self.assertEqual([filter_1.id], action['context']['default_mailing_filter_ids'])
