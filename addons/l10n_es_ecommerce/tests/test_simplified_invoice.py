from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSimplifiedInvoice(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 1. Setup Environment
        cls.company = cls.env.company
        cls.company.country_id = cls.env.ref('base.es').id

        # 2. Create Spanish Partner
        cls.partner_es = cls.env['res.partner'].create({
            'name': 'Spanish Customer',
            'country_id': cls.env.ref('base.es').id,
        })

        # 3. Create Products for Testing (Below and Above Threshold)
        cls.product_cheap = cls.env['product.product'].create({
            'name': 'Cheap Product',
            'list_price': 100.0,
            'invoice_policy': 'order',
        })

        cls.product_expensive = cls.env['product.product'].create({
            'name': 'Expensive Product',
            'list_price': 500.0,
            'invoice_policy': 'order',
        })

        # 4. Get the Simplified Journal from your XML data
        cls.simplified_journal = cls.env.ref('l10n_es_ecommerce.simplified_journal')

        # 5. Force Config Parameters (in case they are not loaded or modified in test DB)
        cls.env['ir.config_parameter'].sudo().set_float('l10n_es_ecommerce.simplified_invoice_limit', 400.0)
        cls.env['ir.config_parameter'].sudo().set_str('l10n_es_ecommerce.default_simplified_journal_id',
                                                        str(cls.simplified_journal.id))

    def test_01_invoice_below_threshold(self):
        """Test that orders below the 400 threshold use the simplified journal and flag."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner_es.id,
            'order_line': [(0, 0, {
                'product_id': self.product_cheap.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })]
        })
        so.action_confirm()

        # Calling standard _create_invoices to trigger override
        invoice = so._create_invoices()

        self.assertEqual(invoice.journal_id.id, self.simplified_journal.id,
                         "Invoice should use the simplified journal when below threshold.")
        self.assertTrue(invoice.l10n_es_is_simplified,
                        "The 'Is Simplified' flag should be checked for the simplified journal.")

    def test_02_invoice_above_threshold(self):
        """Test that orders strictly above the 400 threshold DO NOT use the simplified journal."""
        so = self.env['sale.order'].create({
            'partner_id': self.partner_es.id,
            'order_line': [(0, 0, {
                'product_id': self.product_expensive.id,
                'product_uom_qty': 1,
                'price_unit': 500.0,
            })]
        })
        so.action_confirm()
        invoice = so._create_invoices()

        self.assertNotEqual(invoice.journal_id.id, self.simplified_journal.id, "Invoice should NOT use the simplified journal when above threshold.")
