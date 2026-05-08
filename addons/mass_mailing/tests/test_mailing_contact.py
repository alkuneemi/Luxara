# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from datetime import timedelta

from odoo.fields import Datetime
from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tools import OrderedSet


class TestMailingContact(MassMailCommon):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        # Pepare
        self.env['mailing.contact'].search([('email', '=', False)]).unlink()
        self.contacts = self.env['mailing.contact'].create([
            {'name': 'Contact One', 'email': 'contact.one@company.com'},
            {'name': 'Contact Two', 'email': 'contact.two@company.com'},
            {'name': 'Contact Three', 'email': 'contact.three@company.com'},
            {'name': 'Contact Four', 'email': 'contact.four@company.com'}
        ])
        self.traces = self.env['mailing.trace'].create([
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': self.partner_employee.id,
                'email': self.contacts[0].email,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': self.partner_employee.id,
                'email': self.contacts[0].email,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': self.partner_employee.id,
                'email': self.contacts[1].email,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': self.partner_employee.id,
                'email': self.contacts[1].email,
            },
            {
                'trace_type': 'mail',
                'model': 'mailing.contact',
                'res_id': self.partner_employee.id,
                'email': self.contacts[2].email
            },
        ])
        # Adding traces
        self.traces[0].set_sent()
        self.traces[1].set_sent()
        self.traces[2].set_sent()
        self.traces[3].set_sent()

        self.traces[0].set_opened()
        self.traces[1].set_opened()
        self.traces[2].set_opened()

        self.traces[1].set_replied()

        self.traces[0].set_clicked()
        self.traces[1].set_clicked()
        self.traces[2].set_clicked()

        self.traces[0].open_datetime -= timedelta(days=5)
        self.traces[2].open_datetime -= timedelta(days=6)
        self.traces[1].reply_datetime -= timedelta(days=4)
        self.traces[1].links_click_datetime -= timedelta(days=4)
        self.traces[2].links_click_datetime -= timedelta(days=4)
        self.traces[2].sent_datetime -= timedelta(days=3)

    def test_search_trace_ids(self):
        def date_range_domain(field):
            date_from = today - timedelta(days=30)
            date_to = today
            return ["&", (field, ">=", date_from), (field, "<", date_to)]

        today = Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # (operator, value, expected)
        trace_id_test_params = [
            # contacts that have traces
            ('like', "", self.contacts[:3]),
            ('ilike', "", self.contacts[:3]),
            ('not in', OrderedSet([False]), self.contacts[:3]),
            # contacts that do not have traces
            ('not like', "", self.contacts[3]),
            ('not ilike', "", self.contacts[3]),
            ('in', OrderedSet([False]), self.contacts[3])
        ]
        # (domain, exepected)
        trace_stats_test_params = [
            # Clicked in the last 7 days
            ([("trace_ids", "any", ["&", ("links_click_datetime", ">=", today - timedelta(days=7)), ("links_click_datetime", "<", today)])], self.contacts[:2]),
            # Opened in the last 30 days
            ([("trace_ids", "any", ["&", ("open_datetime", ">=", today - timedelta(days=30)), ("open_datetime", "<", today)])], self.contacts[:2]),
            # Replied in the last 30 days
            ([("trace_ids", "any", ["&", ("reply_datetime", ">=", today - timedelta(days=30)), ("reply_datetime", "<", today)])], self.contacts[0]),
            # Did NOT click in the last 7 days
            ([("trace_ids", "not any", ["&", ("links_click_datetime", ">=", today - timedelta(days=7)), ("links_click_datetime", "<", today)])],
                self.contacts[2] | self.contacts[3]),
            # replied, clicked or opened a mailing the last 30 days
            (
                ["|", "|",
                    ("trace_ids", "any", date_range_domain("links_click_datetime")),
                    ("trace_ids", "any", date_range_domain("open_datetime")),
                    ("trace_ids", "any", date_range_domain("reply_datetime")),
                ], self.contacts[:2]
            ),
            # Did NOT replied, clicked or opened a mailing the last 30 days
            (
                ["!", "|", "|",
                    ("trace_ids", "any", date_range_domain("links_click_datetime")),
                    ("trace_ids", "any", date_range_domain("open_datetime")),
                    ("trace_ids", "any", date_range_domain("reply_datetime")),
                ], self.contacts[2:]
            )
        ]

        # Assert
        for operator, value, expected in trace_id_test_params:
            contacts = self.env['mailing.contact'].search([
                ('trace_ids', operator, value),
                ('email', '!=', False)])
            self.assertEqual(expected, contacts)

        for domain, expected in trace_stats_test_params:
            contacts = self.env['mailing.contact'].search(domain)
            self.assertEqual(expected, contacts)

    def test_search_opened_ratio(self):
        # Prepare
        test_params = [
            ([("opened_ratio", "=", 100)], self.contacts[0]),
            ([("opened_ratio", "=", 50)], self.contacts[1]),
            ([("opened_ratio", ">", 40)], self.contacts[:2]),
            ([("opened_ratio", "=", 0)], self.contacts[2:]),
            ([("opened_ratio", "<", 50)], self.contacts[2:])
        ]

        # Execute & assert
        for domain, expected in test_params:
            contacts = self.env['mailing.contact'].search(domain)
            self.assertEqual(expected, contacts)

    def test_get_dynamic_list_templates_info(self):
        """Verify that the templates have correct domains.
        The method is from the `mailing.filter` model."""
        # Prepare
        ## (template_name, expected)
        test_params = [
            ('start_from_scratch', self.contacts),
            ('recent_sign_ups', self.contacts),
            ('super_fans', self.contacts[0]),
            ('recent_visitors', self.contacts[:2]),
            ('engaged_mailing_contacts', self.contacts[:2]),
            ('disengaged_mailing_contacts', self.contacts[2:]),
        ]
        # Execute & Assert
        for temp_name, expected in test_params:
            domain = self.env['mailing.filter'].get_dynamic_list_templates_info()[temp_name]['domain']
            contacts = self.env['mailing.contact'].search(literal_eval(domain))
            self.assertEqual(expected, contacts)
