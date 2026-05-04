
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveReport(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.overtime_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Overtime Type',
            'requires_allocation': 'yes',
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
            'time_type': 'leave',
        })

    def test_hr_leave_employee_report(self):
        self.env['hr.leave.allocation'].create([
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'date_from': '2025-12-01',
                'number_of_days': '1.875',
            },
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'date_from': '2026-01-01',
                'number_of_days': '12.6875',
            },
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'date_from': '2026-02-01',
                'number_of_days': '1.5',
            },
        ]).action_validate()

        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'request_date_from': '2025-12-02',
                'request_unit_hours': True,
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'request_date_from': '2026-01-02',
                'request_unit_hours': True,
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'request_date_from': '2026-02-02',
                'request_unit_hours': True,
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
        ]).action_validate()

        domain = [
            ('company_id', '=', self.employee_emp.company_id.id),
            ('employee_id', '=', self.employee_emp.id),
            ('leave_type', '=', self.overtime_leave_type.id),
        ]
        leave_balance = self.env['hr.leave.employee.type.report'].search(domain)

        left_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        self.assertEqual(sum(left_allocation.mapped('number_of_hours')), 104.5)
        self.assertEqual(sum(taken_allocation.mapped('number_of_hours')), 24.0)

    def test_overlapping_allocations_leaves_balance(self):
        """Test that leaves deduct correctly when they don't overlap all allocations in a group."""

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Leave Type',
            'requires_allocation': 'yes',
            'leave_validation_type': 'no_validation',
            'request_unit': 'day',
        })

        self.env['hr.leave.allocation'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'date_from': '2024-01-01',
                'date_to': '2025-12-31',
                'number_of_days': 10,
            },
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'date_from': '2025-01-01',
                'date_to': '2026-12-31',
                'number_of_days': 10,
            },
        ]).action_validate()

        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2026-01-01',
                'request_date_to': '2026-01-01',
            },
        ]).action_validate()

        domain = [
            ('employee_id', '=', self.employee_emp.id),
            ('leave_type', '=', leave_type.id),
        ]
        leave_balance = self.env['hr.leave.employee.type.report'].search(domain)

        left_records = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_records = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        # 20 total allocated - 1 taken = 19 remaining
        self.assertEqual(sum(left_records.mapped('number_of_days')), 19)
        self.assertEqual(sum(taken_records.mapped('number_of_days')), 1)
