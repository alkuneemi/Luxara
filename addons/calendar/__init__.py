# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard


def post_init_hook(env):
    # Create primary calendars — constraint silently skips users who already have one
    env.cr.execute("""
                   INSERT INTO calendar_calendar (name, is_primary, user_id, calendar_default_privacy, color, create_uid,
                                                  create_date, write_uid, write_date)
                   SELECT 'Primary Calendar', TRUE, u.id, COALESCE(s.calendar_default_privacy, 'public'), 1, 1, NOW(), 1, NOW()
                     FROM res_users u
                LEFT JOIN res_users_settings s ON s.user_id = u.id
                       ON CONFLICT DO NOTHING
    """)

    # Link existing events to the user's primary calendar
    env.cr.execute("""
                   UPDATE calendar_event e
                      SET calendar_id = c.id
                     FROM calendar_calendar c
                    WHERE e.user_id = c.user_id
                      AND c.is_primary = TRUE
                      AND e.calendar_id IS NULL
    """)

    # Link existing recurrences via their base event
    env.cr.execute("""
                   UPDATE calendar_recurrence r
                      SET calendar_id = c.id
                     FROM calendar_event e
                            JOIN calendar_calendar c
                                 ON c.user_id = e.user_id
                                     AND c.is_primary = TRUE
                    WHERE r.base_event_id = e.id
                      AND r.calendar_id IS NULL
    """)

    env.cr.execute("""
                   INSERT INTO calendar_calendar_filter (user_id, calendar_id, active, is_checked, create_uid,
                                                         create_date, write_uid, write_date)
                   SELECT c.user_id, c.id, TRUE, TRUE, 1, NOW(), 1, NOW()
                     FROM calendar_calendar c
                    WHERE c.is_primary = TRUE
                       ON CONFLICT DO NOTHING
    """)
