# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestChannel(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestChannel, cls).setUpClass()

        cls.channel = cls.env['discuss.channel'].create({'name': 'Test'})

        cls.emp0 = cls.env['hr.employee'].create({
            'user_id': cls.res_users_hr_officer.id,
        })
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
            'member_ids': [(4, cls.emp0.id)],
        })

    def test_auto_join_department(self):
        self.assertEqual(self.channel.channel_partner_ids, self.env['res.partner'])

        self.channel.write({
            'auto_join': True,
            'subscription_department_ids': [(4, self.department.id)]
        })

        self.assertEqual(self.channel.channel_partner_ids, self.department.mapped('member_ids.user_id.partner_id'))

    def test_auto_join_group_department(self):
        self.department.invalidate_recordset(['member_ids'])
        channel = self.env['discuss.channel'].create({
            'name': 'Test group and department',
            'auto_join': True,
            'group_ids': [(4, self.env.ref("base.group_system").id)],
            'subscription_department_ids': [(4, self.department.id)],
        })
        both_partners = self.env.ref('base.user_admin').partner_id | self.emp0.user_id.partner_id
        self.assertEqual(channel.channel_partner_ids, both_partners)
