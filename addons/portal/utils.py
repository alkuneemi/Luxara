# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.tools import consteq


def validate_thread_with_hash_pid(thread, _hash, pid):
    if not _hash or not pid:
        return False
    pid = int(pid)
    if consteq(_hash, thread._sign_token(pid)):
        return True
    parent_sign_token = thread._portal_get_parent_hash_token(pid)
    return parent_sign_token and consteq(_hash, parent_sign_token)


def validate_thread_with_token(thread, token):
    return token and consteq(token, thread[thread._mail_post_token_field])


def get_portal_partner(thread, _hash, pid, token):
    if validate_thread_with_hash_pid(thread, _hash, pid):
        return thread.env["res.partner"].sudo().browse(int(pid))
    if validate_thread_with_token(thread, token):
        if partner := thread._mail_get_partners()[thread.id][:1]:
            return partner
    return thread.env["res.partner"]


def get_portal_message_fetch_domain(records):
    """Return the domain of messages visible on the portal.
    This combines the share visibility domain, the non-empty message domain and
    the model-specific share message types defined by ``_get_share_message_types``."""
    return (
        Domain([("model", "=", records._name), ("res_id", "in", records.ids)])
        & Domain("message_type", "in", records._get_share_message_types())
        & ~records.env["mail.message"]._get_empty_domain()
        & records.env["mail.message"]._get_share_domain()
    )
