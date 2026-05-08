import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { PRODUCT_TEMPLATE_OPTION_SELECTOR } from "./product_template_option";

export class ProductTemplateOptionPlugin extends Plugin {
    static id = "productTemplateOptionPlugin";
    resources = {
        builder_actions: {},
        builder_options_render_context: {
            productTemplateOptionSelector: PRODUCT_TEMPLATE_OPTION_SELECTOR,
        },
    };
}

registry
    .category("website-plugins")
    .add(ProductTemplateOptionPlugin.id, ProductTemplateOptionPlugin);
