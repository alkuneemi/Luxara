import { reactive } from "@web/owl2/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";

class ExtraFieldsPlugin extends Plugin {
    static id = "extraFieldsOption";
    static dependencies = ["remove"];
    static shared = [
        "loadExtraFields",
        "getExtraFields",
        "getCategories",
        "getCategoryCreateMode",
        "setCategoryCreateMode",
        "clearLoadedExtraFields",
    ];

    setup() {
        this._extraFields = reactive([]);
        this._categories = reactive([]);
        this._categoryCreateMode = reactive({ value: false });
        this._loadedExtraFields = null;
        this._pendingUnlinkIds = new Set();
    }

    resources = {
        builder_actions: { AddExtraFieldAction, CreateCategoryAction },

        has_overlay_options: {
            editableOnly: false,
            hasOption: (el) => el.matches("tr[data-extra-field-id]"),
        },

        get_overlay_buttons: withSequence(10, {
            editableOnly: false,
            getButtons: (target) => {
                if (!target.matches("tr[data-extra-field-id]")) {
                    return [];
                }
                return [{
                    class: "oe_snippet_remove text-danger fa fa-trash",
                    title: _t("Remove"),
                    handler: () => this.dependencies.remove.removeElement(target),
                }];
            },
        }),

        on_will_remove_handlers: (toRemoveEl) => {
            if (toRemoveEl.matches("tr[data-extra-field-id]")) {
                const extraFieldId = parseInt(toRemoveEl.dataset.extraFieldId);
                this._pendingUnlinkIds.add(extraFieldId);
                const extraFieldIndex = this._extraFields.findIndex((ef) => ef.id === extraFieldId);
                this._extraFields.splice(extraFieldIndex, 1);
            }
        },

        on_will_save_handlers: async () => {
            if (!this._pendingUnlinkIds.size) return;
            const idsToRemove = [...this._pendingUnlinkIds];
            await this.services.orm.unlink("website.sale.extra.field", idsToRemove);
            this._pendingUnlinkIds.clear();
        },
    };

    getExtraFields() {
        return this._extraFields;
    }


    getCategories() {
        return this._categories;
    }

    getCategoryCreateMode() {
        return this._categoryCreateMode;
    }

    setCategoryCreateMode(value) {
        this._categoryCreateMode.value = value;
    }



    async loadExtraFields() {
        if (!this._loadedExtraFields) {
            const websiteId = this.services.website.currentWebsite.id;

            const [modelFields, categories, extraFields] = await Promise.all([
                this.services.orm.searchRead(
                    "ir.model.fields",
                    [
                        ["model", "=", "product.template"],
                        ["ttype", "in", ["binary", "char", "float"]],
                    ],
                    ["id", "name", "field_description", "model"]
                ),
                this.services.orm.searchRead(
                    "product.attribute.category",
                    [],
                    ["id", "name"]
                ),
                this.services.orm.searchRead(
                    "website.sale.extra.field",
                    [["website_id", "=", websiteId]],
                    ["id", "field_id", "category_id", "label", "name"]
                ),
            ]);

            this._categories.splice(0, this._categories.length, ...categories);
            this._extraFields.splice(0, this._extraFields.length, ...extraFields);

            this._loadedExtraFields = { fields: modelFields };
        }
        return this._loadedExtraFields;
    }

    clearLoadedExtraFields() {
        this._loadedExtraFields = null;
    }
}

class AddExtraFieldAction extends BuilderAction {
    static id = "addExtraField";
    static dependencies = ["extraFieldsOption"];

    setup() {
        this.reload = {};
    }

    async apply({ editingElement }) {
        const fieldId = parseInt(editingElement.dataset.pendingFieldId);
        const categoryId = parseInt(editingElement.dataset.pendingCategoryId) || false;

        if (!fieldId) return;

        const extraFields = this.dependencies.extraFieldsOption.getExtraFields();
        if (extraFields.some((ef) => ef.field_id[0] === fieldId)) return;

        const websiteId = this.services.website.currentWebsite.id;
        await this.services.orm.create(
            "website.sale.extra.field",
            [{ website_id: websiteId, field_id: fieldId, category_id: categoryId }]
        );

        this.dependencies.extraFieldsOption.clearLoadedExtraFields();
    }
}

class CreateCategoryAction extends BuilderAction {
    static id = "createCategory";
    static dependencies = ["extraFieldsOption"];

    async apply({ editingElement }) {
        const name = (editingElement.dataset.pendingNewCategoryName || "").trim();
        if (!name) return;

        const [newId] = await this.services.orm.create(
            "product.attribute.category",
            [{ name }]
        );

        const categories = this.dependencies.extraFieldsOption.getCategories();
        categories.push({ id: newId, name });

        editingElement.dataset.pendingCategoryId = String(newId);
        delete editingElement.dataset.pendingNewCategoryName;
        this.dependencies.extraFieldsOption.setCategoryCreateMode(false);
    }
}

registry.category("website-plugins").add(ExtraFieldsPlugin.id, ExtraFieldsPlugin);
