import { useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ExtraFieldsOption extends BaseOptionComponent {
    static id = "extra_fields_option";
    static template = "website_sale.ExtraFieldsOption";
    static dependencies = ["extraFieldsOption"];

    setup() {
        super.setup();
        const { loadExtraFields, getExtraFields, getCategories } =
            this.dependencies.extraFieldsOption;

        this.sharedState = useState({
            extraFields: getExtraFields(),
            categories: getCategories(),
        });

        this.state = useState({
            fields: [],
            categoryCreateMode: false,
        });

        onWillStart(async () => {
            const extraFieldsData = await loadExtraFields();
            this.state.fields = extraFieldsData.fields;
        });
    }

    setCategoryCreateMode(value) {
        this.state.categoryCreateMode = value;
    }

    onCategoryCreated({ id, name }) {
        this.env.getEditingElement().dataset.pendingCategoryId = String(id);
        this.setCategoryCreateMode(false);
    }
}

registry.category("website-options").add(ExtraFieldsOption.id, ExtraFieldsOption);
