import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { DynamicSnippetParamsAction } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";

const TEMPLATE_OPTIONS = {
    clickable: "website_sale.dynamic_filter_template_product_public_category_clickable_items",
    default: "website_sale.dynamic_filter_template_product_public_category_default",
};

const modelNameFilter = "product.public.category";

const SIZE_CONFIG = {
    small: { span: 2, row: "10vh" },
    medium: { span: 2, row: "15vh" },
    large: { span: 4, row: "15vh" },
};
const ALIGNMENT_CLASSES_MAPPING = {
    left: "justify-content-between",
    center: "align_category_center",
    right: "justify-content-between align_category_right",
};

export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = "dynamicSnippetCategoryOptionPlugin";
    static dependencies = ["dynamicSnippetOption"];

    modelNameFilter = modelNameFilter;
    resources = {
        builder_actions: {
            ToggleClickableAction,
            DynamicCategoryColumnsAction,
            DynamicCategoryGapAction,
            DynamicCategorySizeAction,
            DynamicCategoryAlignmentAction,
            DynamicCategoryParentAction,
            DynamicCategoryShowParentAction,
            DynamicCategoryButtonTextAction,
            DynamicCategoryRoundedAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches("section.s_dynamic_snippet_category")) {
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter,
                [],
                {
                    wrapper_extra_data: {
                        gap: 2,
                        rounded: 2,
                        cols_count: 4,
                        row_size: SIZE_CONFIG.medium.row,
                    },
                    content_extra_data: {
                        size: SIZE_CONFIG.medium.span,
                        alignment_class: ALIGNMENT_CLASSES_MAPPING.center,
                        include_parent: true,
                        col_span_two: true,
                        button_text: _t("Explore Now"),
                    },
                }
            );
        }
    }
}

export class ToggleClickableAction extends BuilderAction {
    static id = "toggleClickable";
    apply({ editingElement }) {
        const dynamicEl = editingElement.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        dynamicParams.content_template_key =
            dynamicParams.content_template_key === TEMPLATE_OPTIONS["default"]
                ? TEMPLATE_OPTIONS["clickable"]
                : TEMPLATE_OPTIONS["default"];
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }
}

class DynamicCategoryColumnsAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategoryColumns";
    getValueInParams({ dynamicParams }) {
        return dynamicParams.wrapper_extra_data.cols_count;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.wrapper_extra_data.cols_count = value;
    }
}

class DynamicCategoryGapAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategoryGap";
    getValueInParams({ dynamicParams }) {
        return dynamicParams.wrapper_extra_data.gap;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.wrapper_extra_data.gap = value;
    }
}

class DynamicCategorySizeAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategorySize";
    isAppliedInParams({ dynamicParams, value }) {
        const { row, span } = SIZE_CONFIG[value];
        return (
            row === dynamicParams.wrapper_extra_data.row_size &&
            span === dynamicParams.content_extra_data.size
        );
    }
    applyInParams({ dynamicParams, value }) {
        const config = SIZE_CONFIG[value];
        dynamicParams.content_extra_data.size = config.span;
        dynamicParams.wrapper_extra_data.row_size = config.row;
    }
    cleanInParams({ dynamicParams }) {
        delete dynamicParams.content_extra_data.size;
        delete dynamicParams.wrapper_extra_data.row_size;
    }
}
class DynamicCategoryAlignmentAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategoryAlignment";
    isAppliedInParams({ dynamicParams, value }) {
        const alignment = ALIGNMENT_CLASSES_MAPPING[value];
        return alignment === dynamicParams.content_extra_data.alignment_class;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.content_extra_data.alignment_class = ALIGNMENT_CLASSES_MAPPING[value];
    }
    cleanInParams({ dynamicParams, value }) {
        delete dynamicParams.content_extra_data.alignment_class;
    }
}
class DynamicCategoryParentAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategoryParent";
    isAppliedInParams({ dynamicParams, value }) {
        return dynamicParams.content_extra_data.parent_category_id === value;
    }
    applyInParams({ dynamicParams, value }) {
        // TODO: there is also `parent_id` used in _prepare_category_list_data
        dynamicParams.content_extra_data.parent_category_id = value;
        dynamicParams.search_domain_extra.parent_id = value;
    }
    cleanInParams({ dynamicParams, value }) {
        delete dynamicParams.content_extra_data.parent_category_id;
        delete dynamicParams.search_domain_extra.parent_id;
    }
}
class DynamicCategoryShowParentAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategoryShowParent";
    isAppliedInParams({ dynamicParams }) {
        return dynamicParams.content_extra_data.include_parent;
    }
    applyInParams({ dynamicParams }) {
        dynamicParams.content_extra_data.include_parent = true;
    }
    cleanInParams({ dynamicParams }) {
        dynamicParams.content_extra_data.include_parent = false;
    }
}

class DynamicCategoryButtonTextAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategoryButtonText";
    getValueInParams({ dynamicParams }) {
        return dynamicParams.content_extra_data.button_text;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.content_extra_data.button_text = value;
    }
}

class DynamicCategoryRoundedAction extends DynamicSnippetParamsAction {
    static id = "dynamicCategoryRounded";
    getValueInParams({ dynamicParams }) {
        return dynamicParams.wrapper_extra_data.rounded;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.wrapper_extra_data.rounded = value;
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetCategoryOptionPlugin.id, DynamicSnippetCategoryOptionPlugin);
