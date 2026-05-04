from odoo import fields, models


class AccountPeppolResponse(models.Model):
    _inherit = 'account.peppol.response'

    response_code = fields.Selection(
        selection_add=[
            ('submitted', 'Submitted'),  # required by PPF
            ('received', 'Received'),  # required by Peppol and PPF; used for PPF messages
            ('made_available', 'Made Available'),  # required by Peppol
            ('approved', 'Approved'),  # used for PPF messages
            ('refused', 'Refused'),  # required by Peppol and PPF; used for PPF messages
            ('paid', '(Partially) Paid'),  # required by PPF
            ('rejected', 'Rejected'),  # required by Peppol and PPF; used for PPF messages
            ('cancelled', 'Cancelled'),
        ],
        ondelete={
            'submitted': 'cascade',
            'received': 'cascade',
            'made_available': 'cascade',
            'approved': 'cascade',
            'refused': 'cascade',
            'paid': 'cascade',
            'rejected': 'cascade',
            'cancelled': 'cascade',
        },
    )
    pdp_ref_response_code = fields.Selection(
        string="Original Response Code",
        selection=[  # Same as `response_code`
            ('submitted', 'Submitted'),
            ('received', 'Received'),
            ('made_available', 'Made Available'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
            ('paid', '(Partially) Paid'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
    )
    pdp_flow_number = fields.Selection(
        string="Flow Number",
        selection=[
            ('1', 'Tax Extract'),
            ('2', 'Status'),
            ('6', 'Mandatory Status'),
            ('10', 'Report'),
        ],
    )
    pdp_fully_paid = fields.Boolean(string="Fully Paid")
    pdp_issue_date = fields.Datetime(string="Issue Date", required=True)
    pdp_status_info = fields.Text(string="Status Info")
