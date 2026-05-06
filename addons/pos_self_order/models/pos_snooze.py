from odoo import api, fields, models


class PosSnooze(models.Model):
    _inherit = 'pos.snooze'

    product_template_id = fields.Many2one('product.template', string='Product', ondelete="cascade", required=False)
    is_self_snoozed = fields.Boolean(string='Is self order snoozed for current config?', default=False)

    _product_or_snoozed_check = models.Constraint(
        'CHECK(product_template_id IS NOT NULL OR is_self_snoozed = TRUE)',
        "Either a product must be set or Self Snoozed must be enabled.",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['is_self_snoozed']

    @api.model
    def _sync_snoozes(self, config, updated_records=None, deleted_record_ids=None):
        super()._sync_snoozes(config, updated_records, deleted_record_ids)
        payload = {
            'deleted_ids': deleted_record_ids if deleted_record_ids else [],
            'records':  self._load_pos_self_data_read(updated_records, config) if updated_records else [],
        }
        config._notify('SNOOZE_CHANGED', payload)
