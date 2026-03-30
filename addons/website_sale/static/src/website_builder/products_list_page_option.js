import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { products_sort_mapping } from "@website_sale/website_builder/shared";
import { onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ProductsListPageOption extends BaseOptionComponent {
    static id = "products_list_page_option";
    static template = "website_sale.ProductsListPageOption";

    setup() {
        super.setup();
        this.products_sort_mapping = products_sort_mapping;

        onPatched(() => {
            if (!this.isBordersOptionVisible) {
                this.env.editor.shared.builderActions.getAction("resetShopStrongBorder").apply();
            }
        });
    }

    get isBordersOptionVisible() {
        return (
            // Is sidebar visible
            this.isActiveItem("categories_opt") ||
            this.isActiveItem("attributes_opt") ||
            // Is product tile not any of the unsupported templates
            (!this.isActiveItem("list_thumbs_view_opt") &&
            !this.isActiveItem("showcase_design_opt") &&
            !this.isActiveItem("bento_design_opt")) ||
            // Is filmstrip visible and not any of the unsupported templates
            (this.isActiveItem("categories_opt_top") && (
            !this.isActiveItem("filmstrip_default_opt") &&
            !this.isActiveItem("filmstrip_images_opt") &&
            !this.isActiveItem("filmstrip_large_images_opt")))
        );
    }
}

registry.category("website-options").add(ProductsListPageOption.id, ProductsListPageOption);
