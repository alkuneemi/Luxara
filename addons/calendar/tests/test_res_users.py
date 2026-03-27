# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.mail.tools.discuss import Store
from odoo.tests.common import tagged, TransactionCase, new_test_user


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResUsers(TransactionCase):

    def test_same_calendar_default_privacy_as_user_template(self):
        """
        The 'calendar default privacy' variable can be set in the Default User Template
        for defining which privacy the new user's calendars will have when creating a
        user. Ensure that when creating a new user, its calendar default privacy will
        have the same value as defined in the template.
        """
        def create_user(name, login, email, privacy=None):
            vals = {'name': name, 'login': login, 'email': email}
            if privacy is not None:
                vals['calendar_default_privacy'] = privacy
            return self.env['res.users'].create(vals)

        # Get Default User Template and define expected outputs for each privacy update test.
        privacy_and_output = [
            (False, 'public'),
            ('public', 'public'),
            ('private', 'private'),
            ('confidential', 'confidential')
        ]
        for (privacy, expected_output) in privacy_and_output:
            # Update default privacy.
            if privacy:
                self.env['ir.config_parameter'].set_str("calendar.default_privacy", privacy)

            # If Calendar Default Privacy isn't defined in vals: get the privacy from Default User Template.
            username = 'test_%s_%s' % (str(privacy), expected_output)
            new_user = create_user(username, username, username + '@user.com')
            self.assertEqual(
                new_user.calendar_default_privacy,
                expected_output,
                'Calendar default privacy %s should be %s, same as in the Default User Template.'
                % (new_user.calendar_default_privacy, expected_output)
            )

            # If Calendar Default Privacy is defined in vals: override the privacy from Default User Template.
            for custom_privacy in ['public', 'private', 'confidential']:
                custom_name = str(custom_privacy) + username
                custom_user = create_user(custom_name, custom_name, custom_name + '@user.com', privacy=custom_privacy)
                self.assertEqual(
                    custom_user.calendar_default_privacy,
                    custom_privacy,
                    'Custom %s privacy from in vals must override the privacy %s from Default User Template.'
                    % (custom_privacy, privacy)
                )

    def test_avoid_res_users_settings_creation_portal(self):
        """
        This test ensures that 'res.users.settings' entries are not created for portal
        and public users through the new 'calendar_default_privacy' field, since it is
        not useful tracking these fields for non-internal users.
        """
        username_and_group = {
            'PORTAL': 'base.group_portal',
            'PUBLIC': 'base.group_public',
        }

        for username, group in username_and_group.items():
            # Create user and impersonate it as sudo for triggering the compute.
            user = self.env['res.users'].create({
                'name': username,
                'login': username,
                'email': username + '@email.com',
                'group_ids': [(6, 0, [self.env.ref(group).id])]
            })
            user.with_user(user).sudo()._compute_calendar_default_privacy()

            # Ensure default privacy fallback and also that no 'res.users.settings' entry got created.
            self.assertEqual(
                user.calendar_default_privacy, 'public',
                "Calendar default privacy of %s users must fallback to 'public'." % (username)
            )
            self.assertFalse(
                user.sudo().res_users_settings_id,
                "No res.users.settings record must be created for '%s' users." % (username)
            )

    def _create_user_for_meeting_status(self):
        return new_test_user(
            self.env,
            login='meeting_status_%s' % self._testMethodName,
            name='Meeting Status %s' % self._testMethodName,
        )

    def _create_event_for_meeting_status(self, user, start, stop, privacy='public'):
        return self.env['calendar.event'].create({
            'name': 'Meeting Status %s' % self._testMethodName,
            'start': start,
            'stop': stop,
            'show_as': 'busy',
            'privacy': privacy,
            'allday': False,
            'attendee_ids': [Command.create({
                'partner_id': user.partner_id.id,
                'state': 'accepted',
            })],
        })

    def _get_main_user_store_values(self, user):
        store_data = Store().add(user.partner_id, "_store_partner_fields")._build_result()
        user_values = next(
            (values for values in store_data.get("res.users", []) if values["id"] == user.id),
            None,
        )
        self.assertTrue(user_values, "The store should contain values for the partner main user.")
        return user_values

    @freeze_time("2026-05-05")
    def test_meeting_status_sent_for_appropriate_event(self):
        user = self._create_user_for_meeting_status()
        now = fields.Datetime.now()
        event = self._create_event_for_meeting_status(
            user,
            start=now - timedelta(minutes=30),
            stop=now + timedelta(hours=1),
        )
        user_values = self._get_main_user_store_values(user)
        self.assertIn(
            'in_meeting_until',
            user_values,
            "in_meeting_until should be sent in main user fields when all meeting conditions are met.",
        )
        self.assertEqual(
            fields.Datetime.to_datetime(user_values['in_meeting_until']),
            event.stop,
            "Stored in_meeting_until should match the meeting stop datetime.",
        )

    @freeze_time("2026-05-05")
    def test_meeting_status_for_private_event(self):
        user = self._create_user_for_meeting_status()
        now = fields.Datetime.now()
        self._create_event_for_meeting_status(
            user,
            start=now - timedelta(minutes=30),
            stop=now + timedelta(hours=1),
            privacy='private',
        )
        self.assertFalse(
            user.in_meeting_until,
            "in_meeting_until should not be set for private events.",
        )
        user_values = self._get_main_user_store_values(user)
        self.assertNotIn(
            'in_meeting_until',
            user_values,
            "in_meeting_until should not be sent in main user fields for private events.",
        )

    @freeze_time("2026-05-05")
    def test_meeting_status_before_meeting_start(self):
        user = self._create_user_for_meeting_status()
        now = fields.Datetime.now()
        self._create_event_for_meeting_status(
            user,
            start=now + timedelta(minutes=30),
            stop=now + timedelta(hours=1, minutes=30),
        )
        self.assertFalse(
            user.in_meeting_until,
            "in_meeting_until should not be set before the meeting start.",
        )
        user_values = self._get_main_user_store_values(user)
        self.assertNotIn(
            'in_meeting_until',
            user_values,
            "in_meeting_until should not be sent in main user fields before meeting start.",
        )
