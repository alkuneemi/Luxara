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
        const { loadExtraFields, getCategories, getExtraFields } =
            this.dependencies.extraFieldsOption;

        const editingElement = this.env.getEditingElement();
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);

        this.sharedState = useState({
            categories: getCategories(),
        });

        this.state = useState({
            availableCategories: [],
            categoryCreateMode: false,
        });

        onWillStart(async () => {
            await loadExtraFields();
            const currentField = getExtraFields().find((ef) => ef.id === extraFieldId);
            const currentCategoryId = currentField?.category_id?.[0] || false;
            const available = getCategories().filter((c) => c.id !== currentCategoryId);
            if (currentCategoryId) {
                available.unshift({ id: "", name: "Others" });
            }
            this.state.availableCategories = available;
        });
    }

    setCategoryCreateMode(value) {
        this.state.categoryCreateMode = value;
    }

    onCategoryCreated({ id, name }) {
        this.env.getEditingElement().dataset.changeExtraFieldCategory = String(id);
        this.state.availableCategories.push({ id, name });
        this.setCategoryCreateMode(false);
    }
}

registry.category("website-options").add(ExtraFieldRowOption.id, ExtraFieldRowOption);
