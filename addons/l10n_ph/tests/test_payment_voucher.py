# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPaymentVoucher(TestPhCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        project_plan, _other_plans = cls.env['account.analytic.plan']._get_all_plans()
        department_plan = cls.env['account.analytic.plan'].create({
            'name': 'Department',
        })
        cls.project_account = cls.env['account.analytic.account'].create({
            'name': 'Project Alpha',
            'plan_id': project_plan.id,
        })
        cls.second_project_account = cls.env['account.analytic.account'].create({
            'name': 'Project Beta',
            'plan_id': project_plan.id,
        })
        cls.department_account_a = cls.env['account.analytic.account'].create({
            'name': 'Department A',
            'plan_id': department_plan.id,
        })
        cls.department_account_b = cls.env['account.analytic.account'].create({
            'name': 'Department B',
            'plan_id': department_plan.id,
        })

    def test_01_plain_text_analytic_distribution_summary(self):
        """Ensure plain text rendering groups totals by analytic plan."""
        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[100.0],
            partner=self.partner_a,
        )
        line = bill.invoice_line_ids
        line.analytic_distribution = {
            f'{self.project_account.id},{self.department_account_a.id}': 20.0,
            f'{self.project_account.id},{self.department_account_b.id}': 80.0,
        }

        text_lines = line._get_analytic_distribution_plain_text().splitlines()
        self.assertEqual(text_lines[0], self.project_account.display_name)
        self.assertEqual(
            text_lines[1],
            f'20% {self.department_account_a.display_name}, 80% {self.department_account_b.display_name}',
        )

    def test_02_plain_text_analytic_distribution_aggregates_combinations(self):
        """Ensure percentages are accumulated across analytic account combinations."""
        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[100.0],
            partner=self.partner_a,
        )
        line = bill.invoice_line_ids
        line.analytic_distribution = {
            f'{self.project_account.id},{self.department_account_a.id}': 20.0,
            f'{self.project_account.id},{self.department_account_b.id}': 30.0,
            f'{self.second_project_account.id},{self.department_account_a.id}': 50.0,
        }

        self.assertEqual(
            line._get_analytic_distribution_plain_text(),
            f'50% {self.project_account.display_name}, 50% {self.second_project_account.display_name}\n'
            f'70% {self.department_account_a.display_name}, 30% {self.department_account_b.display_name}',
        )

    def test_03_plain_text_analytic_distribution_includes_inactive_account(self):
        """Ensure inactive analytic accounts are still resolved in the plain text output."""
        self.department_account_b.active = False

        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[100.0],
            partner=self.partner_a,
        )
        line = bill.invoice_line_ids
        line.analytic_distribution = {
            f'{self.project_account.id},{self.department_account_b.id}': 100.0,
        }

        self.assertEqual(
            line._get_analytic_distribution_plain_text(),
            f'{self.project_account.display_name}\n{self.department_account_b.display_name}',
        )
