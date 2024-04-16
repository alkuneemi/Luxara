import ast
import logging
import typing
from collections import defaultdict
from collections.abc import Iterator

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL, OrderedSet, frozendict, ormcache
from odoo.tools.safe_eval import safe_eval, time
from odoo.tools.translate import _lt

_logger = logging.getLogger(__name__)

OPERATION_SELECTION = {
    'r': 'Read',
    'w': 'Write',
    'rw': 'Read, Write',
    'c': 'Create',
    'rc': 'Read, Create',
    'wc': 'Write, Create',
    'rwc': 'Read, Write, Create',
    'd': 'Delete',
    'rd': 'Read, Delete',
    'wd': 'Write, Delete',
    'rwd': 'Read, Write, Delete',
    'cd': 'Create, Delete',
    'rcd': 'Read, Create, Delete',
    'wcd': 'Write, Create, Delete',
    'rwcd': 'Read, Write, Create, Delete',
}

IN_SELECTION = {
    'read': frozenset(key for key in OPERATION_SELECTION if 'r' in key),
    'write': frozenset(key for key in OPERATION_SELECTION if 'w' in key),
    'create': frozenset(key for key in OPERATION_SELECTION if 'c' in key),
    'unlink': frozenset(key for key in OPERATION_SELECTION if 'd' in key),
}

OPERATION_NAME = {
    'read': _lt("read"),
    'write': _lt("write"),
    'create': _lt("create"),
    'unlink': _lt("unlink"),
}

ACCESS_ERROR_MESSAGE = {
    'read': _lt("You are not allowed to access '%(document_kind)s' (%(document_model)s) records."),
    'write': _lt("You are not allowed to modify '%(document_kind)s' (%(document_model)s) records."),
    'create': _lt("You are not allowed to create '%(document_kind)s' (%(document_model)s) records."),
    'unlink': _lt("You are not allowed to delete '%(document_kind)s' (%(document_model)s) records."),
}


class AccessInfo(typing.NamedTuple):
    """ The data of an ir.access record for a given model, for caching purpose. """
    id: int
    group_id: int  # may be False
    operation: str
    domain: Domain | str


class IrAccess(models.Model):
    """ Access control records with domains. """
    _name = 'ir.access'
    _description = "Access"
    _order = 'model_id, group_id, id'
    _allow_sudo_commands = False

    name = fields.Char()
    active = fields.Boolean(default=True, help="Only active accesses are taken into account when checking access rights.")
    model_id = fields.Many2one('ir.model', string="Model", required=True, ondelete='cascade', index=True)
    group_id = fields.Many2one('res.groups', string="Group", ondelete='cascade', index=True)
    operation = fields.Selection(
        list(OPERATION_SELECTION.items()), required=True, default='rwcd',
        help="Which operation(s) this access applies to, a subset of 'rwcd'.",
    )
    domain = fields.Char()

    for_read = fields.Boolean(
        compute=lambda self: self._compute_for('read'), depends=['operation'],
        compute_sql=lambda self, table: self._compute_for_sql(table, 'read'),
        compute_sudo=False,
        help="Whether this access record applies for operation 'read'",
    )
    for_write = fields.Boolean(
        compute=lambda self: self._compute_for('write'), depends=['operation'],
        compute_sql=lambda self, table: self._compute_for_sql(table, 'write'),
        compute_sudo=False,
        help="Whether this access record applies for operation 'write'",
    )
    for_create = fields.Boolean(
        compute=lambda self: self._compute_for('create'), depends=['operation'],
        compute_sql=lambda self, table: self._compute_for_sql(table, 'create'),
        compute_sudo=False,
        help="Whether this access record applies for operation 'create'",
    )
    for_unlink = fields.Boolean(
        compute=lambda self: self._compute_for('unlink'), depends=['operation'],
        compute_sql=lambda self, table: self._compute_for_sql(table, 'unlink'),
        compute_sudo=False,
        help="Whether this access record applies for operation 'unlink'",
    )

    def _compute_for(self, operation: str):
        field_name = f'for_{operation}'
        operations = IN_SELECTION[operation]
        for access in self:
            access[field_name] = access.operation in operations

    # enables searching, grouping and ordering
    def _compute_for_sql(self, table, operation: str):
        operations = tuple(IN_SELECTION[operation])
        return SQL("(%s IN %s)", table.operation, operations)

    @api.constrains('model_id')
    def _check_model_name(self):
        # Don't allow rules on rules records (this model).
        if any(access.model_id.model == self._name and access.domain for access in self):
            raise ValidationError(self.env._('Accesses with domain can not be applied on model Access itself.'))

    @api.constrains('active', 'domain', 'model_id')
    def _check_domain(self):
        eval_context = self._eval_context()
        for access in self:
            if access.active and access.domain:
                try:
                    domain = safe_eval(access.domain, eval_context)
                    model = self.env[access.model_id.model].sudo()
                    Domain(domain).validate(model)
                except Exception as e:  # noqa: BLE001
                    raise ValidationError(self.env._('Invalid domain %(domain)s: %(error)s', domain=access.domain, error=e))

    #
    # access cache invalidation
    #

    @api.model_create_multi
    def create(self, vals_list):
        # process all pending recomputations with current access rights
        self.env._recompute_all()
        accesses = super().create(vals_list)
        self._clear_caches()
        return accesses

    def write(self, vals):
        # process all pending recomputations with current access rights
        self.env._recompute_all()
        result = super().write(vals)
        self._clear_caches()
        return result

    def unlink(self):
        # process all pending recomputations with current access rights
        self.env._recompute_all()
        result = super().unlink()
        self._clear_caches()
        return result

    def _clear_caches(self):
        """ Invalidate all the caches related to access rights. """
        self.env.invalidate_all()
        self.env.transaction.invalidate_access_cache()
        self.env.registry.clear_cache('stable')

    #
    # access domains and error messages
    #

    @ormcache(cache='stable')
    def _get_all_access(self) -> dict[str, tuple[AccessInfo, ...]]:
        """Return all the active access records as ``AccessInfo`` objects, grouped by model name."""
        accesses = self.sudo().search_fetch(
            [('active', '=', True)],
            ['model_id', 'group_id', 'operation', 'domain'],
            order='id',
        )
        # group accesses by model, and pre-evaluate domains if possible
        result = defaultdict(list)
        env = self.env(su=True)
        for access in accesses:
            model_name = access.model_id.model
            domain = (access.domain or "").strip()
            try:
                domain = ast.literal_eval(domain) if domain else Domain.TRUE
            except ValueError:
                pass
            else:
                domain = Domain(domain).optimize(env[model_name])
            info = AccessInfo(access.id, access.group_id.id, access.operation, domain)
            result[model_name].append(info)

        return frozendict({model_name: tuple(infos) for model_name, infos in result.items()})

    @ormcache('self.env.uid', 'model_name', 'operation', 'include_inherits', 'tuple(self._get_access_context())')
    def _get_domain_for(self, model_name: str, operation: str, *, include_inherits=True) -> Domain:
        """ Return the domain that determines on which records of ``model_name``
        the current user is allowed to perform ``operation``.  The domain comes
        from the permissions and restrictions that applies to the current user.
        If no permission exists for the current user, the method returns ``None``.
        """
        assert operation in IN_SELECTION, f"Invalid access operation {operation!r} (expected 'read', 'write', 'create', 'unlink')"
        operations = IN_SELECTION[operation]

        # collect permissions and restrictions
        permissions = []
        restrictions = []

        # add access for parent models as restrictions
        if include_inherits:
            for parent_model_name, parent_field_name in self.env[model_name]._inherits.items():
                domain = self._get_domain_for(parent_model_name, operation)
                if domain.is_false():
                    return Domain.FALSE
                if not domain.is_true():
                    restrictions.append(Domain(parent_field_name, 'any', domain))

        # include False in user groups to catch global rules
        group_ids = {*self.env.user._get_group_ids(), False}
        # some domains have been pre-evaluated, evaluate only if needed
        eval_context = None
        for access in self._get_all_access().get(model_name, ()):
            if access.operation in operations and access.group_id in group_ids:
                domain = access.domain
                if not isinstance(domain, Domain):
                    if eval_context is None:
                        eval_context = self._eval_context()
                    domain = Domain(safe_eval(domain, eval_context))
                if access.group_id:
                    permissions.append(domain)
                else:
                    restrictions.append(domain)

        return Domain.OR(permissions) & Domain.AND(restrictions)

    def _get_access_context(self) -> Iterator:
        """ Return the context values that the evaluation of the access domain depends on. """
        yield tuple(self.env.context.get('allowed_company_ids', ()))

    def _eval_context(self):
        """Returns a dictionary to use as evaluation context for access domains.
       Note: ``company_ids`` contains the ids of the activated companies by the
       user with the switch company menu. These companies are filtered and trusted.
        """
        # use an empty context for 'user' to make the domain evaluation
        # independent from the context
        return {
            'user': self.env.user.with_context({}),
            'time': time,
            'company_ids': self.env.companies.ids,
            'company_id': self.env.company.id,
        }

    def _make_model_access_error(self, model_name: str, operation: str) -> AccessError:
        """ Return the exception to be raised in case of access error, if the
        current user has no permission at all to perform ``operation`` on the model.
        """
        operation_error = self.env._(ACCESS_ERROR_MESSAGE[operation]) % dict(  # pylint: disable=gettext-variable
            document_kind=self.env['ir.model']._get(model_name).name or model_name,
            document_model=model_name,
        )

        groups = self._get_groups_with_access(model_name, operation)
        if groups:
            group_info = self.env._(
                "This operation is allowed for the following groups:\n%(groups_list)s",
                groups_list="\n".join(f"\t- {group.display_name}" for group in groups),
            )
        else:
            group_info = self.env._("No group currently allows this operation.")

        resolution_info = self.env._("Contact your administrator to request access if necessary.")

        message = f"{operation_error}\n\n{group_info}\n\n{resolution_info}"
        return AccessError(message)

    def _get_groups_with_access(self, model_name: str, operation: str) -> models.Model:
        """ Return the groups that provide permissions for ``operation`` on ``model_name``. """
        assert operation in IN_SELECTION, f"Invalid access operation {operation!r} (expected 'read', 'write', 'create', 'unlink')"
        operations = IN_SELECTION[operation]

        # groups that imply some group having some access record for model
        # FIXME: does not take into account 'access' conditions in domains
        group_ids = OrderedSet(
            access.group_id
            for access in self._get_all_access().get(model_name, ())
            if access.group_id and access.operation in operations
        )
        groups = self.env['res.groups'].sudo().browse(group_ids).all_implied_by_ids

        model = self.env[model_name]
        if model._inherits:
            # groups must also have access to all parent models
            # FIXME: does not take into account overrides of method has_access()
            for parent_model_name in model._inherits:
                groups &= self._get_groups_with_access(parent_model_name, operation)

        return groups.sorted()

    def _make_record_access_error(self, records, operation: str) -> AccessError:
        """ Return the exception to be raised in case of access error. """
        _logger.info(
            "Access Denied for operation: %s on record ids: %r, uid: %s, model: %s",
            operation, records.ids[:6], self.env.uid, records._name,
        )
        self = self.with_context(self.env.user.context_get())  # noqa: PLW0642

        model_name = records._name
        model_description = self.env['ir.model']._get(model_name).name or model_name
        user_description = f"{self.env.user.name} (id={self.env.uid})"
        operation_error = self.env._(
            "Uh-oh! Looks like you have stumbled upon some top-secret records.\n\n"
            "Sorry, %(user)s doesn't have '%(operation)s' access to:",
            user=user_description,
            operation=self.env._(OPERATION_NAME[operation]),  # pylint: disable=gettext-variable
        )
        failing_model = self.env._(
            "- %(description)s (%(model)s)",
            description=model_description, model=model_name,
        )

        resolution_info = self.env._(
            "If you really, really need access, perhaps you can win over your "
            "friendly administrator with a batch of freshly baked cookies."
        )

        # This extended AccessError is only displayed in debug mode.
        # Note that by default, public and portal users do not have the
        # group "base.group_no_one", even if debug mode is enabled, so it is
        # relatively safe here to include the list of accesses and record names.
        accesses = self._get_failed_accesses(records, operation)

        records_sudo = records[:6].sudo()
        company_related = any('company_id' in (access.domain or '') for access in accesses)

        def get_description(record):
            # If the user has access to the company of the record, add this
            # information in the description to help them to change company
            if company_related and 'company_id' in record and record.company_id in self.env.user.company_ids:
                return f'{model_description}, {record.display_name} ({model_name}: {record.id}, company={record.company_id.display_name})'
            return f'{model_description}, {record.display_name} ({model_name}: {record.id})'

        context = None
        if company_related:
            suggested_company = records_sudo._get_redirect_suggested_company()
            if suggested_company and len(suggested_company) > 1:
                resolution_info += "\n\n" + self.env._(
                    "Note: this might be a multi-company issue. "
                    "Switching company may help - in Odoo, not in real life!"
                )
            elif suggested_company and suggested_company in self.env.user.company_ids:
                context = {'suggested_company': {
                    'id': suggested_company.id,
                    'display_name': suggested_company.display_name,
                }}
                resolution_info += "\n\n" + self.env._(
                    "This seems to be a multi-company issue, you might be able "
                    "to access the record by switching to the company: %s.",
                    suggested_company.display_name,
                )
            elif suggested_company:
                resolution_info += "\n\n" + self.env._(
                    "This seems to be a multi-company issue, but you do not "
                    "have access to the proper company to access the record anyhow."
                )

        if self.env.user.has_group('base.group_no_one') and self.env.user._is_internal():
            # this extended AccessError is only displayed in debug mode
            failing_records = '\n'.join(f'- {get_description(record)}' for record in records_sudo)
            access_description = '\n'.join(f'- {access.display_name}' for access in accesses)
            failing_rules = self.env._("Blame the following accesses:\n%s", access_description)
            message = f"{operation_error}\n{failing_records}\n\n{failing_rules}\n\n{resolution_info}"
        else:
            message = f"{operation_error}\n{failing_model}\n\n{resolution_info}"

        # clean up the cache of records prefetched with display_name above
        records.invalidate_recordset()

        exception = AccessError(message)
        if context:
            exception.context = context
        return exception

    def _get_failed_accesses(self, records, operation: str):
        """ Return the access records for the given operation for the current
        user that fail on the given records.

        Can return any permission and/or restriction (since permissions are
        OR-ed together, the entire group succeeds or fails, while restrictions
        are AND-ed and can each fail independently.)
        """
        operations = IN_SELECTION[operation]
        model = records.browse().sudo().with_context(active_test=False)
        eval_context = self._eval_context()

        def eval_domain(access: AccessInfo) -> Domain:
            domain = access.domain
            if isinstance(domain, Domain):
                return domain
            return Domain(safe_eval(domain, eval_context))

        accesses = [
            access
            for access in self._get_all_access().get(model._name, ())
            if access.operation in operations
        ]
        group_ids = set(self.env.user._get_group_ids())

        # first check if the permissions fail for any record (aka if searching
        # on (records, permissions) filters out some of the records)
        permission_domain = Domain.OR(
            eval_domain(access)
            for access in accesses
            if access.group_id in group_ids
        )
        # if all records get returned, the group accesses are not failing
        if len(records.with_env(model.env).filtered_domain(permission_domain)) == len(records):
            group_ids = set()

        # failing accesses are previously selected permissions or any failing restriction
        def is_failing(access: AccessInfo):
            if access.group_id:
                return access.group_id in group_ids
            return len(records.with_env(model.env).filtered_domain(eval_domain(access))) < len(records)

        # FIXME: does not take into account parent model domains (_inherits) and
        # overrides of method has_access()
        return self.sudo().browse(access.id for access in accesses if is_failing(access))
