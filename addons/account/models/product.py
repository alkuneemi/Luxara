from difflib import SequenceMatcher

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import format_amount
from odoo.tools.misc import split_every


ACCOUNT_DOMAIN = "[('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card','off_balance'))]"


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_income_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="This account will be used when validating a customer invoice.",
        tracking=True,
        ondelete='restrict',
    )
    property_account_expense_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.",
        tracking=True,
        ondelete='restrict',
    )

#----------------------------------------------------------
# Products
#----------------------------------------------------------


class ProductTemplate(models.Model):
    _inherit = "product.template"

    taxes_id = fields.Many2many('account.tax', 'product_taxes_rel', 'prod_id', 'tax_id',
        string="Sales Taxes",
        help="Default taxes used when selling the product",
        domain=[('type_tax_use', '=', 'sale')],
        default=lambda self: self.env.companies.account_sale_tax_id or self.env.companies.root_id.sudo().account_sale_tax_id,
    )
    tax_string = fields.Char(compute='_compute_tax_string')
    supplier_taxes_id = fields.Many2many('account.tax', 'product_supplier_taxes_rel', 'prod_id', 'tax_id',
        string="Purchase Taxes",
        help="Default taxes used when buying the product",
        domain=[('type_tax_use', '=', 'purchase')],
        default=lambda self: self.env.companies.account_purchase_tax_id or self.env.companies.root_id.sudo().account_purchase_tax_id,
    )
    property_account_income_id = fields.Many2one('account.account', company_dependent=True, ondelete='restrict',
        string="Income Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category.")
    property_account_income_active = fields.Boolean(related='property_account_income_id.active', string="Income Account Active")
    property_account_expense_id = fields.Many2one('account.account', company_dependent=True, ondelete='restrict',
        string="Expense Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")
    property_account_expense_active = fields.Boolean(related='property_account_expense_id.active', string="Expense Account Active")
    account_tag_ids = fields.Many2many(
        string="Account Tags",
        comodel_name='account.account.tag',
        domain="[('applicability', '=', 'products')]",
        help="Tags to be set on the base and tax journal items created for this product.")
    fiscal_country_codes = fields.Char(compute='_compute_fiscal_country_codes')

    def _get_product_accounts(self):
        return {
            'income': (
                self.property_account_income_id
                or self._get_category_account('property_account_income_categ_id')
                or (self.company_id or self.env.company).income_account_id
            ), 'expense': (
                self.property_account_expense_id
                or self._get_category_account('property_account_expense_categ_id')
                or (self.company_id or self.env.company).expense_account_id
            ),
        }

    def _get_category_account(self, field_name):
        """
        Return the first account defined on the product category hierarchy
        for the given field.
        """
        categ = self.categ_id
        while categ:
            account = categ[field_name]
            if account:
                return account
            categ = categ.parent_id
        return self.env['account.account']

    def get_product_accounts(self, fiscal_pos=None):
        return {
            key: (fiscal_pos or self.env['account.fiscal.position']).map_account(account)
            for key, account in self._get_product_accounts().items()
        }

    @api.depends('company_id')
    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_codes(self):
        for record in self:
            allowed_companies = record.company_id or self.env.companies
            record.fiscal_country_codes = ",".join(allowed_companies.mapped('account_fiscal_country_id.code'))

    @api.depends('taxes_id', 'list_price')
    @api.depends_context('company')
    def _compute_tax_string(self):
        for record in self:
            record.tax_string = record._construct_tax_string(record.list_price)

    def _construct_tax_string(self, price):
        currency = self.currency_id
        res = self.taxes_id._filter_taxes_by_company(self.env.company).compute_all(
            price, product=self, partner=self.env['res.partner']
        )
        joined = []
        included = res['total_included']
        if currency.compare_amounts(included, price):
            joined.append(_('%(amount)s Incl. Taxes', amount=format_amount(self.env, included, currency)))
        excluded = res['total_excluded']
        if currency.compare_amounts(excluded, price):
            joined.append(_('%(amount)s Excl. Taxes', amount=format_amount(self.env, excluded, currency)))
        if joined:
            tax_string = f"(= {', '.join(joined)})"
        else:
            tax_string = " "
        return tax_string

    @api.constrains('uom_id')
    def _check_uom_not_in_invoice(self):
        self.env['product.template'].flush_model(['uom_id'])
        self.env.cr.execute("""
            SELECT prod_template.id
              FROM account_move_line line
              JOIN product_product prod_variant ON line.product_id = prod_variant.id
              JOIN product_template prod_template ON prod_variant.product_tmpl_id = prod_template.id
              JOIN uom_uom template_uom ON prod_template.uom_id = template_uom.id
              JOIN uom_uom line_uom ON line.product_uom_id = line_uom.id
             WHERE prod_template.id IN %s
               AND line.parent_state = 'posted'
               AND template_uom.id != line_uom.id
             LIMIT 1
        """, [tuple(self.ids)])
        if self.env.cr.fetchall():
            raise ValidationError(_(
                "This product is already being used in posted Journal Entries.\n"
                "If you want to change its Unit of Measure, please archive this product and create a new one."
            ))

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'combo':
            self.taxes_id = False
            self.supplier_taxes_id = False
        return super()._onchange_type()

    def _force_default_sale_tax(self, companies):
        default_customer_taxes = companies.filtered('account_sale_tax_id').account_sale_tax_id
        if not default_customer_taxes:
            return
        links = [Command.link(t.id) for t in default_customer_taxes]
        for sub_ids in split_every(self.env.cr.IN_MAX, self.ids):
            chunk = self.browse(sub_ids)
            chunk.write({'taxes_id': links})
            chunk.invalidate_recordset(['taxes_id'])

    def _force_default_purchase_tax(self, companies):
        default_supplier_taxes = companies.filtered('account_purchase_tax_id').account_purchase_tax_id
        if not default_supplier_taxes:
            return
        links = [Command.link(t.id) for t in default_supplier_taxes]
        for sub_ids in split_every(self.env.cr.IN_MAX, self.ids):
            chunk = self.browse(sub_ids)
            chunk.write({'supplier_taxes_id': links})
            chunk.invalidate_recordset(['supplier_taxes_id'])

    def _force_default_tax(self, companies):
        self._force_default_sale_tax(companies)
        self._force_default_purchase_tax(companies)

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        # If no company was set for the product, the product will be available for all companies and therefore should
        # have the default taxes of the other companies as well. sudo() is used since we're going to need to fetch all
        # the other companies default taxes which the user may not have access to.
        other_companies = self.env['res.company'].sudo().search(['!', ('id', 'child_of', self.env.companies.ids)])
        if other_companies and products:
            products_without_company = products.filtered(lambda p: not p.company_id).sudo()
            products_without_company._force_default_tax(other_companies)
        return products

    def _get_list_price(self, price):
        """ Get the product sales price from a public price based on taxes defined on the product """
        self.ensure_one()
        if not self.taxes_id:
            return super()._get_list_price(price)
        computed_price = self.taxes_id.compute_all(price, self.currency_id)
        total_included = computed_price["total_included"]

        if price == total_included:
            # Tax is configured as price included
            return total_included
        # calculate base from tax
        included_computed_price = self.taxes_id.with_context(force_price_include=True).compute_all(price, self.currency_id)
        return included_computed_price['total_excluded']

    def _get_price_diff_account(self):
        self.ensure_one()
        return False


class ProductProduct(models.Model):
    _inherit = "product.product"

    tax_string = fields.Char(compute='_compute_tax_string')

    def _get_product_accounts(self):
        return self.product_tmpl_id._get_product_accounts()

    def _get_default_product_values(self, company, document_type):
        """ Get the default product values for a document type.

        :param document_type:   The type of the document.
        :return:                A dictionary of default product values.
        """
        self.ensure_one()

        uom = self.uom_id

        if document_type == 'sale':
            taxes = self.taxes_id._filter_taxes_by_company(company)
        elif document_type == 'purchase':
            taxes = self.supplier_taxes_id._filter_taxes_by_company(company)
        else:
            taxes = self.env['account.tax']

        if document_type == 'sale':
            price = self.with_company(company).lst_price
        elif document_type == 'purchase':
            price = self.with_company(company).standard_price
        else:
            price = 0.0

        if document_type == 'sale':
            currency = self.currency_id
        elif document_type == 'purchase':
            currency = company.currency_id

        return {
            'product': self,
            'price': price,
            'uom': uom,
            'taxes': taxes,
            'currency': currency,
            'document_tax_mode': None,
        }

    @api.model
    def _adapt_product_values_to_currency(self, product_values, currency, conversion_date):
        """ Adapt the product values to the given currency at a specific date.

        :param product_values:  The product values created by '_get_default_product_values'.
        :param currency:        The currency to adapt to.
        :param conversion_date: The date to use for the currency conversion.
        :return:                A dictionary of adapted product values.
        """
        product_currency = product_values['currency']

        if product_currency != currency:
            price = product_currency._convert(
                product_values['price'],
                currency,
                product_values['company'],
                conversion_date,
                round=False,
            )
        else:
            price = product_values['price']

        return {
            **product_values,
            'price': price,
            'currency': currency,
        }

    @api.model
    def _adapt_product_values_to_document_tax_mode(self, product_values, document_tax_mode, get_opposite_tax_mode_value=False):
        """ Adapt the product values to the tax mode forced for the document.

        :param product_values:               The product values created by '_get_default_product_values'.
        :param document_tax_mode:            The tax mode forced for the document.
        :param get_opposite_tax_mode_value:  True when the tax mode of the company that is then applied on the product is different than the tax mode forced on the document.
        :return:                A dictionary of adapted product values.
        """
        if document_tax_mode is None or not get_opposite_tax_mode_value:
            return product_values

        results = product_values['taxes']._get_tax_details(
            price_unit=product_values['price'],
            quantity=1.0,
            rounding_method='round_globally',
            product=product_values['product'],
            product_uom=product_values['uom'],
            document_tax_mode=product_values['document_tax_mode'],
        )
        if document_tax_mode == 'tax_included':
            price = results['total_included']
        else:
            price = results['total_excluded']

        return {
            **product_values,
            'price': price,
            'document_tax_mode': document_tax_mode,
        }

    @api.model
    def _adapt_product_values_to_uom(self, product_values, uom):
        """ Adapt the product values to the given uom.

        :param product_values:  The product values created by '_get_default_product_values'.
        :param uom:             The uom to adapt to.
        :return:                A dictionary of adapted product values.
        """
        product_uom = product_values['uom']

        # Apply unit of measure.
        if product_uom and product_uom != uom:
            price = product_uom._compute_price(product_values['price'], uom)
        else:
            price = product_values['price']

        return {
            **product_values,
            'uom': uom,
            'price': price,
        }

    @api.model
    def _adapt_product_values_to_fiscal_position(self, product_values, fiscal_position):
        """ Adapt the product values to the fiscal position.

        :param product_values:  The product values created by '_get_default_product_values'.
        :param fiscal_position: The fiscal position to adapt to.
        :return:                A dictionary of adapted product values.
        """
        product = product_values['product']
        price = product_values['price']
        taxes = product_values['taxes']

        if taxes and fiscal_position:
            taxes_after_fp = fiscal_position.map_tax(taxes)
            if taxes != taxes_after_fp:
                price = taxes._adapt_price_unit_to_another_taxes(
                    price_unit=price,
                    product=product,
                    original_taxes=taxes,
                    new_taxes=taxes_after_fp,
                    document_tax_mode=product_values['document_tax_mode'],
                )
                taxes = taxes_after_fp

        return {
            **product_values,
            'price': price,
            'taxes': taxes,
        }

    @api.model
    def _price_is_from_product(self, line, document_type):
        """ Validates the line price by comparing it against a re-computation based on
        the price_unit_json snapshot from the previous execution.

        :param line:            Line from account.move, sale.order or purchase.order.
        :param document_type:   The type of the document.
        :return:                Boolean indicating if price is computed from product.
        """
        if line.price_unit_json:
            uom = self.env['uom.uom'].browse(line.price_unit_json['uom_id']) if line.price_unit_json['uom_id'] else None
            dtm = line.price_unit_json['document_tax_mode'] if line.price_unit_json['document_tax_mode'] else None
        else:
            uom = dtm = None
        price_from_product = self._get_tax_included_unit_price(
            company=line.company_id,
            currency=line.currency_id,
            document_date=line.move_id.date if 'move_id' in line._fields else line.order_id.date_order,
            document_type=document_type,
            fiscal_position=line.move_id.fiscal_position_id if 'move_id' in line._fields else line.order_id.fiscal_position_id,
            product_uom=uom,
            document_tax_mode=dtm,
            get_opposite_tax_mode_value=(dtm != line.company_id.account_price_include) if dtm else False,
        )
        return price_from_product == line.price_unit

    def _get_line_price_unit(self, line, document_type, price=0.0):
        """ Helper for account.move, sale.order and purchase.order to get the price unit
        in various cases, even when there isn't a specified product.

        :param line:            Line from account.move, sale.order or purchase.order.
        :param document_type:   The type of the document.
        :return:                Unit price after adapting it to any changes made on the line.
        """

        product = self
        if line.price_unit_json:
            uom = self.env['uom.uom'].browse(line.price_unit_json['uom_id']) if line.price_unit_json['uom_id'] else None
            dtm = line.price_unit_json['document_tax_mode'] if line.price_unit_json['document_tax_mode'] else None
            document_tax_mode_changed = line.price_unit_json['document_tax_mode'] != line.document_tax_mode
        else:
            uom = line.product_id.uom_id
            dtm = line.company_id.account_price_include
            document_tax_mode_changed = False
        product_values = {
            'product': line.product_id,
            'uom': uom,
            'price': price if not line.price_unit else line.price_unit,
            'taxes': line.tax_ids,
            'document_tax_mode': dtm,
            'currency': line.currency_id,
        }
        get_opposite_tax_mode_value = line.document_tax_mode != line.company_id.account_price_include
        line_uom = line.uom_id if 'uom_id' in line._fields else line.product_uom_id

        if product and not price and (
            not line.price_unit_json or not line.price_unit_json['product_id'] or line.price_unit_json['product_id'] != line.product_id.id or product._price_is_from_product(line, document_type)
        ):
            return line.product_id._get_tax_included_unit_price(
                product_price_unit=price,
                company=line.company_id,
                currency=line.currency_id,
                document_date=line.move_id.date if 'move_id' in line._fields else line.order_id.date_order,
                document_type=document_type,
                fiscal_position=line.move_id.fiscal_position_id if 'move_id' in line._fields else line.order_id.fiscal_position_id,
                product_uom=line_uom,
                document_tax_mode=line.document_tax_mode,
                get_opposite_tax_mode_value=get_opposite_tax_mode_value,
            )
        else:
            apply_document_tax_mode = (not line.price_unit_json and not price) or (line.price_unit_json and line.price_unit_json['document_tax_mode'] != line.document_tax_mode)
            if apply_document_tax_mode:
                product_values = product._adapt_product_values_to_document_tax_mode(product_values, line.document_tax_mode, get_opposite_tax_mode_value=get_opposite_tax_mode_value or document_tax_mode_changed)

            apply_uom = (not line.price_unit_json and not price) or (line.price_unit_json and line.price_unit_json['uom_id'] != line_uom.id)
            if apply_uom:
                product_values = product._adapt_product_values_to_uom(product_values, line_uom)

            return product_values['price']

    def _get_tax_included_unit_price(self, company, currency, document_date, document_type,
        is_refund_document=False, product_uom=None, product_currency=None,
        product_price_unit=None, product_taxes=None, fiscal_position=None,
        document_tax_mode=None, get_opposite_tax_mode_value=None, product_values=None,
    ):
        """ Helper to get the price unit from different models.
            This is needed to compute the same unit price in different models (sale order, account move, etc.) with same parameters.
        """
        self.ensure_one()

        product_values = self._get_default_product_values(company, document_type)
        if product_currency:
            product_values['currency'] = product_currency
        if product_taxes:
            product_values['taxes'] = product_taxes
        if product_price_unit:
            product_values['price'] = product_price_unit

        product_values = self._adapt_product_values_to_document_tax_mode(product_values, document_tax_mode, get_opposite_tax_mode_value)
        product_values = self._adapt_product_values_to_uom(product_values, product_uom)
        product_values = self._adapt_product_values_to_fiscal_position(product_values, fiscal_position)
        product_values = self._adapt_product_values_to_currency(product_values, currency, document_date)

        return product_values['price']

    def _get_tax_included_unit_price_from_price(
        self, product_price_unit, product_taxes,
        fiscal_position=None,
        product_taxes_after_fp=None,
        document_tax_mode=None,
    ):
        if not product_taxes:
            return product_price_unit

        if product_taxes_after_fp is None:
            if not fiscal_position:
                return product_price_unit

            product_taxes_after_fp = fiscal_position.map_tax(product_taxes)

        return product_taxes._adapt_price_unit_to_another_taxes(
            price_unit=product_price_unit,
            product=self,
            original_taxes=product_taxes,
            new_taxes=product_taxes_after_fp,
            document_tax_mode=document_tax_mode,
        )

    @api.depends('lst_price', 'product_tmpl_id', 'taxes_id')
    @api.depends_context('company')
    def _compute_tax_string(self):
        for record in self:
            record.tax_string = record.product_tmpl_id._construct_tax_string(record.lst_price)

    def _get_opposite_tax_mode_price(self, line, price_from_product):
        '''Helper to get the opposite tax mode price_unit when switching between tax included and excluded
        for different models: account_move, sale_order and purchase_order.

        :param line:                 Either an account_move_line, sale_order_line or purchase_order_line.
        :param price_from_product:   Price normally computed from _get_tax_included_unit_price that has already
                                     dealt with currency, fiscal position and unit of measure.

        :return:                     The price calculated using the opposite tax mode set on the product which
                                     follows the tax mode set on the company.
        '''
        self.ensure_one()
        product = self
        total_price_mapping = {
            'tax_included': 'total_excluded',
            'tax_excluded': 'total_included',
        }
        product_tax_mode = line.company_id.account_price_include
        return line.tax_ids._filter_taxes_by_company(line.company_id)._get_tax_details(
            price_from_product,
            1.0,
            rounding_method='round_globally',
            product=product,
            product_uom=line.product_uom_id if 'product_uom_id' in line._fields else line.uom_id,
            document_tax_mode=product_tax_mode,
        )[total_price_mapping[product_tax_mode]]

    # -------------------------------------------------------------------------
    # EDI
    # -------------------------------------------------------------------------

    def _retrieve_product(self, company=None, extra_domain=None, **product_vals):
        '''Search all products and find one that matches one of the parameters.

        :param company:         The company of the product.
        :param extra_domain:    Any extra domain to add to the search.
        :param product_vals:    Values the product should match.
        :returns:               A product or an empty recordset if not found.
        '''
        company = company or self.env.company
        company_domains = (
            [*self.env['res.partner']._check_company_domain(company), ('company_id', '!=', False)],
            [('company_id', '=', False)],
        )

        def find_product_by_name_similarity():
            """ Returns the first product whose name similarity ratio with the provided name meets
            the threshold set in the system parameter.
            """
            name = (product_vals.get('name') or '').split('\n', 1)[0]  # Cut sales description from the name

            # checking length to avoid matching unrelated products whose names merely contain that short string
            if len(name) <= 4:
                return False

            # Get similarity threshold from system parameter, fallback to 0.9 if missing, invalid, or out of range (0, 1].
            try:
                similarity_threshold = self.env['ir.config_parameter'].sudo().get_float('account.product_name_similarity_threshold', 0.9)
                if similarity_threshold <= 0.0 or similarity_threshold > 1.0:
                    similarity_threshold = 0.9
            except ValueError:
                similarity_threshold = 0.9

            for company_domain in company_domains:
                products = self.search(
                    Domain.AND([
                        [('name', 'ilike', name)],
                        company_domain,
                        extra_domain or Domain.TRUE,
                    ]),
                )
                for product in products:
                    if SequenceMatcher(None, name.lower(), product.name.lower()).ratio() >= similarity_threshold:
                        return product

            return False

        domains = self._get_product_domain_search_order(**product_vals)
        for _priority, domain in domains:
            for company_domain in company_domains:
                if product := self.env['product.product'].search(
                    Domain.AND([domain, company_domain, extra_domain or Domain.TRUE]), limit=1,
                ):
                    return product

        if product := find_product_by_name_similarity():
            return product
        return self.env['product.product']

    def _get_product_domain_search_order(self, **vals):
        """Gives the order of search for a product given the parameters.

        :param name:            The name of the product.
        :param default_code:    The default_code of the product.
        :param barcode:         The barcode of the product.
        :returns:               An ordered list of product domains and their associated priority.
        :rtype: list[tuple[int, Domain]]
        """
        sorted_domains = []
        if barcode := vals.get('barcode'):
            sorted_domains.append((5, Domain('barcode', '=', barcode)))
        if default_code := vals.get('default_code'):
            sorted_domains.append((10, Domain('default_code', '=', default_code)))
        if name := vals.get('name'):
            name = name.split('\n', 1)[0]  # Cut sales description from the name
            sorted_domains.append((15, Domain('name', '=ilike', name)))
        return sorted_domains

    def _get_price_diff_account(self):
        return self.product_tmpl_id._get_price_diff_account()
