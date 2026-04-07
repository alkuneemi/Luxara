# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init_hook(env):
    env['res.company'].sudo().search([]).apply_worldline_branding()


def uninstall_hook(env):
    env['res.company'].sudo().search([]).reset_worldline_branding()
