from functools import cache
from importlib import import_module
import logging
import psycopg2

from odoo.addons.base.models.res_users import _check_apikey_credentials
from odoo.exceptions import ValidationError
from odoo.http import Controller, route
from odoo.modules import Manifest
from odoo.release import series as release_series
from odoo.sql_db import db_connect

_logger = logging.getLogger(__name__)


@cache  # no need to call more than once per worker
def _get_kpi_providers():
    """
    Load KPI provider functions declared by addons from the addons path.

    Scan all available addon manifests and look for a ``kpi_providers`` entry.
    This entry is expected to be a list of strings in the form ``'module.path:function'``
    where the module path is resolved relative to ``odoo.addons.<addon>.<module.path>``.

    Invalid or non-loadable providers are ignored (and logged).

    Returns:
        tuple[(addon_name, kpi_provider_fn)]
    """
    kpi_providers = []
    for manifest in Manifest.all_addon_manifests():
        if not manifest:
            continue
        # kpi_providers should be a list of strings in the form 'pkg.module:function'
        # where 'pkg.module' is relative to the addon
        for kpi_provider in manifest.get('kpi_providers', []):
            if kpi_provider[0] == '.':
                _logger.warning('Invalid KPI provider hook path %r in addon %r', kpi_provider, manifest.name)
                continue

            try:
                module, function = kpi_provider.split(':', 1)
                mod = import_module(f'.{module}', package=f'odoo.addons.{manifest.name}')
                fn = getattr(mod, function)
            except Exception:
                _logger.exception('Failed to import KPI provider %r from addon %r', kpi_provider, manifest.name)
                continue

            if not callable(fn):
                _logger.warning('KPI provider %r from addon %r is not callable', kpi_provider, manifest.name)
                continue

            kpi_providers.append((manifest.name, fn))

    return tuple(kpi_providers)


def _db_kpi_summary(database, api_key):
    """
    Retrieve the KPI summary from a single database
    """
    try:
        cursor = db_connect(database).cursor()
    except psycopg2.Error:
        # Avoid leaking information about missing database to prevent scanning databases hosted on the same server
        return

    with cursor as cr:
        cr.execute("SELECT latest_version FROM ir_module_module WHERE name = 'base'")
        db_version, = cr.fetchone()
        if not db_version.startswith(release_series):
            _logger.error("database %r has version %r that doesn't match running version %r",
                          database, db_version, release_series)
            return  # behave as if the database does not exist

        uid = _check_apikey_credentials(cr, scope='rpc', key=api_key)
        if not uid:
            _logger.error("invalid api key for database %r", database)
            return  # behave as if the database does not exist

        kpi_summary = []
        for module, get_kpi_summary in _get_kpi_providers():
            try:
                kpi_summary.extend(get_kpi_summary(cr, uid))
            except Exception:  # noqa: BLE001
                message = f"get_kpi_summary error in module {module!r}"
                _logger.exception(message)
                return {'error': message}

        cr.execute("""
            SELECT u.id,
                   p.name,
                   u.login,
                   (SELECT MAX(create_date)
                      FROM res_users_log log
                      WHERE log.create_uid = u.id) login_date
              FROM res_users u
              JOIN res_partner p ON u.partner_id = p.id
             WHERE u.active
               AND not u.share
        """)
        users = cr.dictfetchall()

        return {
            'database_version': release_series,
            'kpi_summary': kpi_summary,
            'users': users,
        }


class KpiController(Controller):
    @route('/kpi/summary', type='jsonrpc', auth='none', save_session=False)
    def kpi_summary(self, credentials):
        """
        Retrieve the KPI summaries from a batch of databases hosted on the same server.
        The result of this call will only include the databases:
            - that have been found on this server
            - where the provided API key could be verified
            - that are on the same Odoo version as the current Odoo

        Databases that don't match one of these points won't be included in the result,
        and should be contacted separately via RPC calls.

        :param credentials: a list of [db_name, api_key] pairs
        :return A dictionary with db_name as keys and as value a dictionary with keys 'version', 'users' and 'kpi_summary',
                or with key 'error' if an error occurred.
        """
        if len(credentials) > 500:
            raise ValidationError(self.env._("Too many credentials"))

        result = {}
        for database, api_key in credentials:
            try:
                db_result = _db_kpi_summary(database, api_key)
                if db_result is not None:
                    result[database] = db_result
            except Exception:  # noqa: BLE001
                _logger.exception("get_kpi_summary error")
        return result
