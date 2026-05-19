from odoo import models, fields, api


class CrmLeadFunnel(models.Model):
    _inherit = 'crm.lead'

    # ── Funnel position ────────────────────────────────────────────────────────
    current_funnel_step = fields.Selection(
        selection=[
            ('1_categories', 'زار الأقسام الرئيسية'),
            ('2_types',      'زار الأنواع'),
            ('3_subtypes',   'زار الأنواع الفرعية'),
            ('4_form',       'مرحلة ملء الاستمارة'),
            ('5_payment',    'مرحلة الدفع'),
            ('6_completed',  'أكمل العملية بنجاح'),
        ],
        string='Funnel Step',
        tracking=True,
        index=True,
    )

    # ── Last visited records ───────────────────────────────────────────────────
    last_category_id = fields.Many2one(
        'insurance.category', string='Last Category', ondelete='set null')
    last_type_id = fields.Many2one(
        'insurance.type', string='Last Type', ondelete='set null')
    last_subtype_id = fields.Many2one(
        'insurance.subtype', string='Last Subtype', ondelete='set null')

    # ── Journey log ───────────────────────────────────────────────────────────
    journey_log_ids = fields.One2many(
        'crm.lead.journey.log', 'lead_id', string='Journey Log')
    journey_log_count = fields.Integer(
        compute='_compute_journey_log_count', string='Log Entries')

    @api.depends('journey_log_ids')
    def _compute_journey_log_count(self):
        for rec in self:
            rec.journey_log_count = len(rec.journey_log_ids)

    # ── Core funnel helper ────────────────────────────────────────────────────
    def _funnel_advance(self, step, action_name, page_url=None, **extra_vals):
        """
        Atomically:
          1. Move the funnel step forward (never backward).
          2. Update any extra field values (last_category_id, etc.).
          3. Append a timestamped journey log entry.
        Designed to be called with sudo() from controllers.
        """
        self.ensure_one()
        current = self.current_funnel_step or ''
        write_vals = dict(extra_vals)

        if not current or step > current:
            write_vals['current_funnel_step'] = step

        if write_vals:
            self.write(write_vals)

        # Always log every visit, even if step didn't change
        self.env['crm.lead.journey.log'].create({
            'lead_id': self.id,
            'action_name': action_name,
            'page_url': page_url or '',
        })

        # Auto-mark Won on completion
        if step == '6_completed':
            won_stage = self.env['crm.stage'].sudo().search(
                [('is_won', '=', True)], limit=1)
            if won_stage:
                self.write({'stage_id': won_stage.id, 'probability': 100})

        return self


class CrmLeadJourneyLog(models.Model):
    _name = 'crm.lead.journey.log'
    _description = 'CRM Lead — Website Journey Log'
    _order = 'id desc'
    _log_access = True  # auto create_date / create_uid

    lead_id = fields.Many2one(
        'crm.lead', string='Lead',
        required=True, ondelete='cascade', index=True)
    action_name = fields.Char(string='Action', required=True)
    page_url = fields.Char(string='Page URL')
    create_date = fields.Datetime(string='Timestamp', readonly=True)
