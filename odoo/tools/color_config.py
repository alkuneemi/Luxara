import configparser
import logging
from collections import ChainMap
from optparse import OptionValueError
from os import getenv, isatty

from odoo.tools import config

logger = logging.getLogger(__name__)

AUTO = ('auto',)  # Colorize only in the terminal
YES = ('1', 'yes', 'true', 'on', 'always')  # Always colorize
NO = ('0', 'no', 'false', 'off', 'never')  # Never colorize

# Append the following to your ~/.odoorc configuration file:
"""
[color]
pid = never
session_id = never
loglevel = auto
http_request_line = auto
http_response_size = auto
query_count = auto
query_time = auto
remaining_time = auto
cursor_mode = auto
"""


def color2bool(color: str | bool, is_a_tty: bool) -> bool:
    if color in (True, False):
        return color
    if color.lower() in AUTO:
        return is_a_tty
    if color.lower() in YES:
        return True
    if color.lower() in NO:
        return False
    e = f"{color.lower()!r} is not one of {'/'.join(AUTO + YES + NO)}"
    raise ValueError(e)


class _ColorConfig:
    def __init__(self):
        self._default_options = {
            'pid': False,
            'session_id': False,
            'loglevel': True,
            'http_request_line': True,
            'http_response_size': True,
            'query_count': True,
            'query_time': True,
            'remaining_time': True,
            'cursor_mode': True,
        }
        self._file_options = {}
        self._force_options = {}
        self._runtime_options = {}

        self._options = ChainMap(
            self._runtime_options,
            self._force_options,
            self._file_options,
            self._default_options,
        )

    def reload(self):
        is_a_tty = any(
            isinstance(handler, logging.StreamHandler)
            and hasattr(handler.stream, 'fileno')
            and isatty(handler.stream.fileno())
            for handler in logging.getLogger().handlers
        )

        if not is_a_tty:
            self._default_options.update(dict.fromkeys(self._default_options, False))

        force = (color2bool(c, is_a_tty) if (c := getenv('ODOO_PY_COLORS'))
            else False if getenv('NO_COLOR')
            else True if getenv('FORCE_COLOR')
            else None
        )
        if force is not None:
            self._force_options = dict.fromkeys(self._default_options, force)

        p = configparser.RawConfigParser()
        try:
            p.read([config['config']])
            file_options = p.items('color')
        except (OSError, configparser.NoSectionError):
            pass
        else:
            self._file_options.clear()
            for name, value in file_options:
                if name not in self._default_options:
                    logger.warning("unknown color option: %r, skipped", name)
                    continue
                try:
                    self._file_options[name] = color2bool(value, is_a_tty)
                except ValueError as exc:
                    e = f"color option {name}: invalid value: {value!r}"
                    raise OptionValueError(e) from exc

    def __getitem__(self, key):
        return self._options[key]

    def __setitem__(self, key, item):
        if key not in self._default_options:
            raise KeyError(key)
        self._options[key] = item  # it writes in _running_options


color_config = _ColorConfig()
