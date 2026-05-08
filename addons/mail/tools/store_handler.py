import logging
from collections.abc import Iterable
from typing import Literal, NamedTuple, get_args

from odoo.exceptions import AccessError
from odoo.http.routing_map import Controller
from odoo.addons.mail.tools.discuss import Store

_logger = logging.getLogger(__name__)

AUDIENCE = Literal["everyone", "logged_in", "internal"]
ALLOWED_AUDIENCE = get_args(AUDIENCE)


class StoreHandler(NamedTuple):
    audience: AUDIENCE
    func_name: str
    readonly: bool


class StoreHandlerRegistry(dict[str, StoreHandler]):
    def add(
        self, name: str, func_name: str, audience: AUDIENCE = "internal", readonly: bool = False
    ):
        assert audience in ALLOWED_AUDIENCE, (
            f"Invalid audience {audience} for mail store "
            f"handler {name} with function {func_name}"
        )
        assert name not in self, (
            f"Mail store handler {name} already registered "
            f"with a different function: {self[name].func_name} vs {func_name}"
        )
        self[name] = StoreHandler(audience=audience, func_name=func_name, readonly=readonly)

    def execute_for_user(self, controller: Controller, store: Store, fetch_params: Iterable | str):
        if not isinstance(controller, Controller):
            raise TypeError(
                "Controller must be an instance of odoo.http.routing_map.Controller"
            )
        for fetch_param in fetch_params:
            name, params, data_id = (
                (fetch_param, None, None)
                if isinstance(fetch_param, str)
                else (fetch_param + [None, None])[:3]
            )
            store.data_id = data_id
            if not (entry := self.get(name)):
                _logger.warning("No mail store handler registered for %s", name)
                continue
            assert entry.func_name.startswith("store"), (
                "Mail store handler functions must start with 'store'"
                " to avoid potential security issues"
            )
            user = controller.env.user
            if (
                entry.audience == "everyone"
                or (entry.audience == "logged_in" and not user._is_public())
                or (entry.audience == "internal" and user._is_internal())
            ):
                # getattr is used to ensure we get the inherited method when the controller is extended,
                # `entry.func_name` is only to be registered with the `mail_handler` decorator,
                # to ensure the function exists and to avoid potential security issues.
                handler = getattr(controller, entry.func_name)
                if params is None:
                    handler(store)
                elif isinstance(params, dict):
                    handler(store, **params)
                elif isinstance(params, list):
                    handler(store, *params)
                else:
                    handler(store, params)
            else:
                raise AccessError(
                    controller.env._("User does not have access to mail store handler %s", name)
                )
        store.data_id = None

    def is_fetch_readonly(self, fetch_params: Iterable | str) -> bool:
        for fetch_param in fetch_params:
            name = fetch_param if isinstance(fetch_param, str) else fetch_param[0]
            if (entry := self.get(name)) and not entry.readonly:
                return False
        return True


store_handler_registry = StoreHandlerRegistry()


def store_handler(
    name: str | None = None, audience: AUDIENCE = "internal", readonly: bool = True
):
    def store_handler__decorator(func):
        if name:
            store_handler_registry.add(
                name, func.__name__, audience=audience, readonly=readonly
            )
        return func

    return store_handler__decorator
