from odoo import fields, models


class PdpResponse(models.Model):
    _name = 'pdp.response'
    _description = 'Response Messages for PDP'

    peppol_message_uuid = fields.Char('Peppol Message UUID', required=True)
    flow_number = fields.Selection(
        selection=[
            ('1', 'Tax Extract'),
            ('2', 'Status'),
            ('6', 'Mandatory Status'),
            ('10', 'Report'),
        ],
        default="2",
        required=True,
    )
    response_code = fields.Selection(
        selection=[
            ('submitted', 'Submitted'),  # required by PPF
            ('received', 'Received'),  # required by Peppol and PPF
            ('made_available', 'Made Available'),  # required by Peppol
            ('approved', 'Approved'),
            ('refused', 'Refused'),  # required by Peppol and PPF
            ('paid', 'Paid'),  # required by PPF
            ('rejected', 'Rejected'),  # required by Peppol and PPF
            ('cancelled', 'Cancelled'),
        ],
    )
    pdp_state = fields.Selection(
        selection=[
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
            ('not_serviced', 'Not Serviced'),
        ],
        string='French E-Invoicing Status',
        required=True,
    )
    ppf_state = fields.Selection(
        string="PPF State",
        selection=[
            ("received", "Transmission Received"),
            ("inadmissible", "Transmission Refused"),
            ("rejected", "Rejected"),
            ("accepted", "Accepted"),
        ],
        help="Note that we do not receive 'Accepted' for flow 6 lifecycles (they stay at 'Transmission Received' or will be 'Rejected')",
    )
    status_info = fields.Text()
    issue_date = fields.Datetime(string="Issue Date", required=True)
    move_id = fields.Many2one('account.move', ondelete='cascade', required=True)
    company_id = fields.Many2one(related='move_id.company_id')
