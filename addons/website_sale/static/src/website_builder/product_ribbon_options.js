import { useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ProductsRibbonOption extends BaseOptionComponent {
    static id = "products_ribbon_option";
    static template = 'website_sale.ProductsRibbonOptionPlugin';
    static dependencies = ['productsRibbonOptionPlugin'];

    setup() {
        super.setup();

        const {loadInfo, getCount} = this.dependencies.productsRibbonOptionPlugin;
        this.count = useState(getCount());

        this.state = useState({
            ribbons: [],
            ribbonEditMode: false,
        });

        this.domState = useDomState(async (el) => {
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;
            const variantMode =
                (el.closest("#product_detail") && el.querySelector(".variant_attribute")) ||
                !templateId;

            return {
                variantMode,
            };
        });

        onWillStart(async () => {
            this.state.ribbons = await loadInfo();
        });
    }
}

registry.category("website-options").add(ProductsRibbonOption.id, ProductsRibbonOption);
