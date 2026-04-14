from odoo import Command, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """ Check if there are pending payments on other companies that wait for this move. """
        posted_moves = super()._post(soft)
        posted_invoices = posted_moves.filtered(
            lambda move: move.is_invoice()
               and move.payment_state in ('not_paid', 'partial')
               and move.company_id.account_interco_clearing_journal_id
               and move.company_id not in move.sudo().mapped("transaction_ids.payment_id.company_id")
        )

        for invoice in posted_invoices:
            if payments := invoice.sudo().mapped('transaction_ids.payment_id').filtered(
                lambda x: x.state in ('in_process', 'paid')
                   and x.company_id != invoice.company_id
                   and x.company_id.account_interco_clearing_journal_id.id
            ):
                invoice._check_interco_clearing(payments)
        return posted_moves

    def _check_interco_clearing(self, payments):
        self.ensure_one()
        label = f'{fields.Date.to_string(self.invoice_date)} / {self.partner_id.display_name} / {self.name}'
        for payment in payments:
            _liquidity_lines, counterpart_lines, _writeoff_lines = payments._seek_for_lines()
            # reconcile payment entry (if present)
            if counterpart_lines:
                counterpart_account = counterpart_lines.account_id
                counterpart_balance = sum(line.credit for line in counterpart_lines)
                payment_clearing = self.env['account.move'].with_company(payment.company_id).create({
                    'move_type': 'entry',
                    'journal_id': payment.company_id.account_interco_clearing_journal_id.id,
                    'ref': payment.memo,
                    'line_ids': [
                        Command.create({
                            'name': label,
                            'account_id': counterpart_account.id,
                            'partner_id': self.partner_id.id,
                            'currency_id': payment.currency_id.id,
                            'amount_currency': payment.amount,
                            'debit': counterpart_balance,
                        }),
                        Command.create({
                            'name': label,
                            'account_id': payment.company_id.account_interco_payable_id.id,
                            'partner_id': self.company_id.partner_id.id,
                            'currency_id': payment.currency_id.id,
                            'amount_currency': -payment.amount,
                            'credit': counterpart_balance,
                        }),
                    ]
                })
                payment_clearing.action_post()
                payment_clearing_line = payment_clearing.line_ids.filtered(lambda line: line.account_id == counterpart_account)
                (counterpart_lines + payment_clearing_line).reconcile()

        # Reconcile invoice
        other_base_amount = payment.currency_id._convert(
            payment.amount,
            self.company_id.currency_id,
            self.company_id,
            self.invoice_date,
        )
        invoice_ar_line = self.line_ids.filtered(lambda acc: acc.account_type == 'asset_receivable')[:1]
        payment_partner = payment.company_id.partner_id

        entry = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'entry',
            'journal_id': self.company_id.account_interco_clearing_journal_id.id,
            'ref': f"Interco Settlement - {payment.memo}",
            'line_ids': [
                Command.create({
                    'name': label,
                    'account_id': self.company_id.account_interco_receivable_id.id,
                    'partner_id': payment_partner.id,
                    'currency_id': self.company_id.currency_id.id,
                    'amount_currency': payment.amount,
                    'balance': other_base_amount,
                }),
                Command.create({
                    'name': label,
                    'account_id': invoice_ar_line.account_id.id,
                    'partner_id': payment.partner_id.id,
                    'currency_id': self.company_id.currency_id.id,
                    'amount_currency': -payment.amount,
                    'balance': -other_base_amount,
                }),
            ],
        })
        entry.action_post()
        entry_receivable_line = entry.line_ids.filtered(lambda line: line.account_id == invoice_ar_line.account_id)
        (entry_receivable_line + invoice_ar_line).reconcile()
