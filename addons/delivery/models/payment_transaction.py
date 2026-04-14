# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _post_process(self):
        """Override of `payment` to confirm orders with the cash_on_delivery payment method and
        trigger a picking creation."""
        cod_pending_txs = self.filtered(
            lambda tx: tx.provider_id.custom_mode == "cash_on_delivery" and tx.state == "pending"
        )
        cod_pending_txs.sale_order_ids.filtered(lambda so: so.state == "draft").with_context(
            send_email=True
        ).action_confirm()
        super()._post_process()

    def _filtered_paid_on_delivery(self):
        return self.filtered_domain(self._get_paid_on_delivery_domain())

    def _filtered_pending_delivery(self):
        return self.filtered_domain(
            self._get_paid_on_delivery_domain() & Domain("state", "=", "pending")
        )

    def _get_paid_on_delivery_domain(self):
        pms_on_delivery = self.env["payment.method"]._get_payment_method_on_delivery_codes()
        return Domain("payment_method_id.code", "in", pms_on_delivery)

    def _confirm_payment_on_delivery(self, *, orders_not_to_followup=None):
        """Confirm transactions created using a "Pay on Delivery" payment method, and trigger the
        post process cron.

        If the order's `amount_on_delivery` to be collected is lower than the remaining balance,
        the last transaction is split into two new transactions: 1. to confirm the
        `amount_on_delivery`, and 2. to follow the remaining balance.

        :param sale.order orders_not_to_followup: Order for which followup transactions should not
            be created.
        :raises UserError: If the latest transaction is outdated.
        :return: The confirmed transaction(s). May include newly created transactions.
        :rtype: payment.transaction
        """
        orders_not_to_followup = orders_not_to_followup or self.env["sale.order"]

        delivered_txs, followup_txs = self.browse(), self.browse()
        for order, pending_delivery_txs in (
            self._filtered_pending_delivery().grouped("sale_order_ids").items()
        ):
            order.ensure_one()
            last_tx = pending_delivery_txs._get_last()
            remaining_balance = order.amount_total - order.amount_paid

            # Ensure the last transaction is not outdated.
            assert order.currency_id == last_tx.currency_id
            if order.currency_id.compare_amounts(remaining_balance, last_tx.amount) > 0:
                raise UserError(
                    self.env._(
                        "The remaining balance of the order cannot exceed the amount authorized by"
                        " the customer. Please consider generating a new payment link."
                        "\n\n- Remaining Balance (%(order)s): %(remaining_balance)s"
                        "\n- Authorized Amount (%(tx)s): %(tx_amount)s",
                        order=order.display_name,
                        remaining_balance=order.currency_id.format(remaining_balance),
                        tx=last_tx.display_name,
                        tx_amount=order.currency_id.format(last_tx.amount),
                    )
                )

            # Cancel all the other pending transactions linked to the same SO.
            if old_txs := pending_delivery_txs - last_tx:
                old_txs._set_canceled_in_favor_of(last_tx)

            delivered_tx, followup_tx = last_tx._split_on_delivered_amount(
                skip_followup=order in orders_not_to_followup
            )
            delivered_txs |= delivered_tx
            followup_txs |= followup_tx

        delivered_txs._set_done()
        followup_txs._set_pending()
        if delivered_txs:
            self.env.ref("payment.cron_post_process_payment_tx")._trigger()

        return delivered_txs

    def _split_on_delivered_amount(self, *, skip_followup=False):
        """Compare the `amount_on_delivery` of the transaction's order and split if it is lower than
        the transaction's amount.

        :param bool skip_followup: Whether to skip the followup transaction.
        :return: A tuple of the delivered/confirmed transaction, and the followup transaction if
            created.
        :rtype: tuple[payment.transaction, payment.transaction]
        """
        self.ensure_one()
        order = self.sale_order_ids.ensure_one()
        assert order.currency_id == self.currency_id
        Tx = self.env["payment.transaction"]

        cmp = self.currency_id.compare_amounts(order.amount_on_delivery, self.amount)
        if not cmp:  # order.amount_on_delivery == self.amount
            return self, Tx
        if cmp > 0:  # order.amount_on_delivery > self.amount (shouldn't be possible)
            raise UserError(
                self.env._(
                    "The collected amount cannot exceed the authorized amount."
                    " Please contact Odoo support or generate a new payment link."
                )
            )

        remaining_balance = order.amount_total - order.amount_paid
        if not self.currency_id.compare_amounts(remaining_balance, order.amount_on_delivery):
            # If both amounts are equal, no followup transaction is needed. We still create a new
            # transaction because `order.amount_on_delivery` is lower than `self.amount`.
            skip_followup = True

        # The order was either not fully delivered, or its remaining balance decreased since this
        # transaction was created. Create a transaction for the delivered amount and, unless
        # `skip_followup` is set, another one for the remaining payment.
        split_vals = self._prepare_delivery_transaction_split_vals(skip_followup=skip_followup)

        txs = Tx.create(split_vals)
        self._set_canceled_in_favor_of(txs)

        return txs[:1], txs[1:]

    def _prepare_delivery_transaction_split_vals(self, *, skip_followup=False):
        self.ensure_one()
        order = self.sale_order_ids.ensure_one()
        source_tx = self.source_transaction_id or self
        base_vals = self.copy_data({
            "source_transaction_id": source_tx.id,
            "sale_order_ids": [Command.set(order.ids)],
        })[0]

        def compute_reference(idx_):
            return f"{source_tx.reference}-{len(source_tx.child_transaction_ids) + idx_}"

        split_vals = [
            {**base_vals, "amount": order.amount_on_delivery, "reference": compute_reference(1)}
        ]
        if not skip_followup:
            split_vals.append({
                **base_vals,
                "amount": self.amount - order.amount_on_delivery,
                "reference": compute_reference(2),
            })

        return split_vals

    def _set_canceled_in_favor_of(self, favored_txs):
        self._set_canceled(
            state_message=self.env._(
                "Canceled in favor of %(favored_txs)s.",
                favored_txs=", ".join(favored_txs.mapped("display_name")),
            )
        )
