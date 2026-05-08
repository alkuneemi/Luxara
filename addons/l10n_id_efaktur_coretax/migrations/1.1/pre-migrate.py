# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import sql


def migrate(cr, version):
    """Copy legacy ``l10n_id_tku`` into ``additional_identifiers['TKU']`` on upgrade (idempotent)."""
    if not sql.column_exists(cr, 'res_partner', 'l10n_id_tku'):
        return
    if not sql.column_exists(cr, 'res_partner', 'additional_identifiers'):
        return
    cr.execute("""
        UPDATE res_partner AS p
        SET additional_identifiers = COALESCE(p.additional_identifiers, '{}'::jsonb)
            || jsonb_build_object('TKU', to_jsonb(trim(p.l10n_id_tku)))
        WHERE COALESCE(trim(p.l10n_id_tku), '') <> ''
          AND NOT COALESCE(p.additional_identifiers, '{}'::jsonb) ? 'TKU'
    """)
