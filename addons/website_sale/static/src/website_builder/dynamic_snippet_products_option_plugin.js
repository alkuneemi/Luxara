import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getContextualFilterDomain } from "./dynamic_snippet_products_option";
import { DynamicSnippetParamsAction } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";

export class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "dynamicSnippetProductsOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    static shared = ["fetchCategories", "getModelNameFilter"];
    modelNameFilter = "product.product";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        builder_actions: {
            DynamicProductShowVariantsAction,
            DynamicProductCategoryAction,
        },
        dynamic_filter_search_domain_processors: (
            domain,
            { productRibbonIds, productTagIds, productNames }
        ) => {
            if (productRibbonIds?.length) {
                const ribbonIds = productRibbonIds.map((productRibbon) => productRibbon.id);
                domain.push(
                    "|",
                    ["variant_ribbon_id", "in", ribbonIds],
                    "&",
                    ["variant_ribbon_id", "=", false],
                    ["product_tmpl_id.website_ribbon_id", "in", ribbonIds]
                );
            }
            if (productTagIds?.length) {
                domain.push(["all_product_tag_ids", "in", productTagIds.map((e) => e.id)]);
            }
            if (productNames) {
                const nameDomain = [];
                for (const productName of productNames.split(",")) {
                    // Ignore empty names
                    if (!productName.length) {
                        continue;
                    }
                    // Search on name, internal reference and barcode.
                    if (nameDomain.length) {
                        nameDomain.unshift("|");
                    }
                    nameDomain.push(
                        ...[
                            "|",
                            "|",
                            ["name", "ilike", productName],
                            ["default_code", "=", productName],
                            ["barcode", "=", productName],
                        ]
                    );
                }
                domain.push(...nameDomain);
            }
        },
    };
    setup() {
        this.categories = undefined;
    }
    destroy() {
        super.destroy();
        this.categories = undefined;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_products")) {
            await this.dependencies.dynamicSnippetCarouselOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter,
                getContextualFilterDomain(this.editable),
                {
                    search_domain_extra: {
                        product_category: "all",
                        hide_variants: false,
                    },
                }
            );
        }
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async fetchCategories() {
        if (!this.categories) {
            this.categories = this._fetchCategories();
        }
        return this.categories;
    }
    async _fetchCategories() {
        // TODO put in an utility function
        const websiteDomain = [
            "|",
            ["website_id", "=", false],
            ["website_id", "=", this.services.website.currentWebsite.id],
        ];
        return this.services.orm.searchRead(
            "product.public.category",
            websiteDomain,
            ["id", "name"],
            { order: "name asc" }
        );
    }
}

class DynamicProductShowVariantsAction extends DynamicSnippetParamsAction {
    static id = "dynamicProductShowVariants";
    isAppliedInParams({ dynamicParams }) {
        return !dynamicParams.search_domain_extra.hide_variants;
    }
    applyInParams({ dynamicParams }) {
        dynamicParams.search_domain_extra.hide_variants = false;
    }
    cleanInParams({ dynamicParams }) {
        dynamicParams.search_domain_extra.hide_variants = true;
    }
}

class DynamicProductCategoryAction extends DynamicSnippetParamsAction {
    static id = "dynamicProductCategory";
    isAppliedInParams({ dynamicParams, value }) {
        return dynamicParams.search_domain_extra.product_category === value;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.search_domain_extra.product_category = value;
    }
    cleanInParams({ dynamicParams }) {
        delete dynamicParams.search_domain_extra.product_category;
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetProductsOptionPlugin.id, DynamicSnippetProductsOptionPlugin);
