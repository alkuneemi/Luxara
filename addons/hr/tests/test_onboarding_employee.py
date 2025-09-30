# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import HttpCase, tagged, users

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestOnboardingEmployee(HttpCase):
    @users('admin')
    def test_load_sample_data(self):
        """ Assert that the 'Load sample button' of the onboarding action helper is displayed and works
            It should only be displayed when one of the displayed company is 'base.main_company' and
            when the company still doesn't contain any employee
        """
        main_company_domain = [['company_id', '=', self.env.ref('base.main_company').id]]
        if self.env['hr.employee'].search_count(main_company_domain):
            _logger.warning("Employee(s) detected in he DB, skipping the test TestOnboardingEmployee.test_load_sample_data...")
            return

        self.start_tour('/odoo', 'load_employee_sample_data_tour', login=self.env.user.login)
        employees = self.env["hr.employee"].search(main_company_domain)
        self.assertEqual(len(employees), 3, "The 3 sample employees should've been loaded.")
