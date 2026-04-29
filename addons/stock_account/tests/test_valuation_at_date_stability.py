from datetime import timedelta

from freezegun import freeze_time

from odoo.fields import Datetime
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


class TestValuationAtDateStability(TestStockValuationCommon):

    def _make_inventory_adjustment(self, product, quantity, inventory_location=None):
        if not inventory_location:
            inventory_location = product.property_stock_inventory
            inventory_location.company_id = self.env.company.id
        move = self.env['stock.move'].create({
            'location_id': inventory_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product.id,
            'product_uom': self.uom.id,
            'product_uom_qty': quantity,
        })
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.quantity = quantity
        move.picked = True
        move._action_done()
        return move

    def test_fifo_at_date_stable_after_new_receipt(self):
        """ Inventory adjustment valued at std_price=10 should keep its
        historical value after a new receipt changes standard_price.
        """
        product = self.product_fifo
        product.standard_price = 10

        now = Datetime.now()
        date1 = now - timedelta(days=5)
        date2 = now - timedelta(days=3)

        # adjust 10 units in at std_price 10
        with freeze_time(date1):
            adj = self._make_inventory_adjustment(product, 10)

        self.assertEqual(adj.value, 100.0)
        self.assertEqual(product.with_context(to_date=Datetime.to_string(date1)).total_value, 100.0)

        value_before = product.with_context(to_date=Datetime.to_string(date1)).total_value

        # receive 10@20, changes std_price
        with freeze_time(date2):
            self._make_in_move(product, 10, unit_cost=20)

        self.assertNotEqual(product.standard_price, 10.0)

        value_after = product.with_context(to_date=Datetime.to_string(date1)).total_value
        self.assertEqual(value_before, value_after)

    def test_fifo_at_date_stable_after_price_decrease(self):
        """ Same as above but with a price decrease. """
        product = self.product_fifo
        product.standard_price = 20

        now = Datetime.now()
        date1 = now - timedelta(days=5)
        date2 = now - timedelta(days=3)

        with freeze_time(date1):
            self._make_inventory_adjustment(product, 10)

        value_before = product.with_context(to_date=Datetime.to_string(date1)).total_value
        self.assertEqual(value_before, 200.0)

        # receive 10@5
        with freeze_time(date2):
            self._make_in_move(product, 10, unit_cost=5)

        self.assertLess(product.standard_price, 20.0)

        value_after = product.with_context(to_date=Datetime.to_string(date1)).total_value
        self.assertEqual(value_before, value_after)

    def test_fifo_at_date_stable_multiple_adjustments(self):
        """ Multiple inventory adjustments, then a receipt at a very different
        price. Historical valuation at intermediate date must remain stable.
        """
        product = self.product_fifo
        product.standard_price = 10

        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=6)
        date3 = now - timedelta(days=3)

        # adjust 5 units
        with freeze_time(date1):
            self._make_inventory_adjustment(product, 5)

        # adjust 5 more
        with freeze_time(date2):
            self._make_inventory_adjustment(product, 5)

        value_at_date2 = product.with_context(to_date=Datetime.to_string(date2)).total_value
        self.assertEqual(value_at_date2, 100.0)

        # receive 10@50
        with freeze_time(date3):
            self._make_in_move(product, 10, unit_cost=50)

        self.assertGreater(product.standard_price, 10.0)
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).total_value,
            value_at_date2,
        )
