import { useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ExtraFieldRowOption extends BaseOptionComponent {
    static id = "extra_field_row_option";
    static template = "website_sale.ExtraFieldRowOption";
    static dependencies = ["extraFieldsOption"];

    setup() {
        super.setup();
        const { loadExtraFields, getCategories, getExtraFields, getState } =
            this.dependencies.extraFieldsOption;

        const editingElement = this.env.getEditingElement();
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);
        getState().rowCategoryId = null;

        this.sharedState = useState({
            categories: getCategories(),
            optionState: getState(),
        });

        this.state = useState({
            currentCategoryId: false,
        });

        onWillStart(async () => {
            await loadExtraFields();
            const currentExtraField = getExtraFields().find(
                (extraField) => extraField.id === extraFieldId
            );
            const currentCategoryId = currentExtraField?.category_id?.[0] || false;
            this.state.currentCategoryId = currentCategoryId;
        });
    }

    setCategoryCreateMode(value) {
        this.sharedState.optionState.rowCategoryCreateMode = value;
    }

    getAvailableCategories() {
        const available = this.sharedState.categories.filter(
            (category) => category.id !== this.state.currentCategoryId
        );
        if (this.state.currentCategoryId) {
            return [{ id: "", name: "Others" }, ...available];
        }
        return available;
    }
}

registry.category("website-options").add(ExtraFieldRowOption.id, ExtraFieldRowOption);
