# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_mrp.tests.test_multistep_manufacturing import TestMultistepManufacturing
from odoo.tests import common


@common.tagged('post_install', '-at_install')
class TestSaleMrpAccount(TestMultistepManufacturing):
    def test_mo_get_project_from_so(self):
        """ ensure the project of MO is inherited from the SO if no project is set """
        project = self.env['project.project'].create({
            'name': 'SO Project',
        })
        self.sale_order.project_id = project
        self.assertFalse(self.sale_order.mrp_production_ids.project_id)
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.mrp_production_ids.project_id, project)

    def test_mo_get_project_from_so_in_2_steps_delivery(self):
        """ Ensure the project of MO is inherited from the SO in a 2-step delivery (Pick + Ship). """
        self.warehouse.delivery_steps = 'pick_ship'

        # Change Routes and Rules to have the following configuration:
        #    - Step 1: Test/Stock (location_src_id) > Test/Output (location_dest_id)
        #    - Step 2: Test/Output (location_src_id) > Parteners/Customers (location_dest_id)
        output_loc = self.warehouse.delivery_route_id.rule_ids.filtered(lambda r: r.action == 'push').location_src_id
        self.warehouse.delivery_route_id.rule_ids.filtered(lambda r: r.action == 'pull').write({'location_dest_id': output_loc.id})
        if self.warehouse.mto_pull_id.location_dest_id == self.env.ref('stock.stock_location_customers'):
            self.warehouse.mto_pull_id.write({'location_dest_id': output_loc.id})
        self.warehouse.delivery_route_id.rule_ids.filtered(lambda r: r.action == 'push').write({'action': 'pull'})

        product_service = self.env['product.product'].create({
            'name': 'Furniture Assembly',
            'type': 'service',
            'service_tracking': 'project_only',
        })

        self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'name': product_service.name,
            'product_id': product_service.id,
            'product_uom_qty': 1.0,
            'price_unit': 50.0,
        })

        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.mrp_production_ids.project_id)
