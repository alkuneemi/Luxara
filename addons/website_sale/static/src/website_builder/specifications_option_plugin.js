import { reactive } from "@web/owl2/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

class SpecificationsPlugin extends Plugin {
    static id = "specificationsOption";
    static dependencies = ["builderOptions", "remove"];
    static shared = [
        "loadSpecs",
        "getExtraFields",
        "getCategories",
        "getCategoryCreateMode",
        "setCategoryCreateMode",
        "clearLoadedSpecs",
    ];

    resources = {
        builder_actions: {
            AddSpecFieldAction,
            RemoveSpecFieldAction,
            CreateCategoryAction,
        },
        is_unremovable_selectors: "tr[data-extra-field-id]",
        has_overlay_options: {
            editableOnly: false,
            hasOption: (el) =>
                el.matches("tr[data-extra-field-id]") &&
                !el.dataset.pendingRemove,
        },
        get_overlay_buttons: withSequence(10, {
            editableOnly: false,
            getButtons: (target) => {
                if (
                    !target.matches("tr[data-extra-field-id]") ||
                    target.dataset.pendingRemove
                ) {
                    return [];
                }
                return [
                    {
                        class: "oe_snippet_remove text-danger fa fa-trash",
                        title: _t("Remove"),
                        handler: () => {
                            const recordId = parseInt(
                                target.dataset.extraFieldId
                            );
                            if (!recordId) return;

                            target.dataset.pendingRemove = "1";
                            target.style.display = "none";

                            const extraFields = this._extraFields;
                            const idx = extraFields.findIndex(
                                (ef) => ef.id === recordId
                            );
                            if (idx !== -1) {
                                extraFields.splice(idx, 1);
                            }

                            this.dependencies.builderOptions.deactivateContainers();
                        },
                    },
                ];
            },
        }),

        on_will_save_handlers: async () => {
            const pendingRows = [
                ...this.editable.querySelectorAll(
                    "tr[data-extra-field-id][data-pending-remove]"
                ),
            ];
            if (!pendingRows.length) return;

            const ids = pendingRows.map((row) =>
                parseInt(row.dataset.extraFieldId)
            );

            await this.services.orm.unlink("website.sale.extra.field", ids);
            this.clearLoadedSpecs();
            for (const row of pendingRows) {
                delete row.dataset.pendingRemove;
            }
        },
    };

    setup() {
        this._extraFields = reactive([]);
        this._categories = reactive([]);
        this._categoryCreateMode = reactive({ value: false });
        this._loadedSpecs = null;
    }

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

    async loadSpecs() {
        if (!this._loadedSpecs) {
            const websiteId = this.services.website.currentWebsite.id;

            const [rawFields, categories, extraFields] = await Promise.all([
                this.services.orm.searchRead(
                    "ir.model.fields",
                    [
                        ["model", "=", "product.template"],
                        ["ttype", "in", ["char", "binary", "float"]],
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

            const fields = rawFields;

            this._categories.splice(0, this._categories.length, ...categories);
            this._extraFields.splice(0, this._extraFields.length, ...extraFields);

            this._loadedSpecs = { fields };
        }
        return this._loadedSpecs;
    }

    clearLoadedSpecs() {
        this._loadedSpecs = null;
    }
}

class AddSpecFieldAction extends BuilderAction {
    static id = "addSpecField";
    static dependencies = ["specificationsOption", "builderOptions"];

    setup() {
        this.canTimeout = false;
        this.reload = true;
    }

    async apply({ editingElement }) {
        const fieldId = parseInt(editingElement.dataset.pendingFieldId);
        const categoryId =
            parseInt(editingElement.dataset.pendingCategoryId) || false;

        if (!fieldId) {
            return;
        }

        const extraFields = this.dependencies.specificationsOption.getExtraFields();
        const alreadyExists = extraFields.some(
            (ef) => ef.field_id[0] === fieldId
        );
        if (alreadyExists) {
            return;
        }

        const websiteId = this.services.website.currentWebsite.id;

        await this.services.orm.create(
            "website.sale.extra.field",
            [{ website_id: websiteId, field_id: fieldId, category_id: categoryId }]
        );

        this.dependencies.specificationsOption.clearLoadedSpecs();
        this.dependencies.builderOptions.setNextTarget(editingElement);
    }
}

class RemoveSpecFieldAction extends BuilderAction {
    static id = "removeSpecField";
    static dependencies = ["specificationsOption"];
    setup() {
        this.canTimeout = false;
        this.reload = true;
    }
    async apply({ editingElement, value }) {
        const recordId = parseInt(value);
        if (!recordId) return;
        await this.services.orm.unlink("website.sale.extra.field", [recordId]);
        this.dependencies.specificationsOption.clearLoadedSpecs();
    }
}

class CreateCategoryAction extends BuilderAction {
    static id = "createCategory";
    static dependencies = ["specificationsOption", "builderOptions"];

    setup() {
        this.canTimeout = false;
        this.reload = false;
    }

    async apply({ editingElement }) {
        const name = (editingElement.dataset.pendingNewCategoryName || "").trim();
        if (!name) {
            return;
        }

        const [newId] = await this.services.orm.create(
            "product.attribute.category",
            [{ name }]
        );

        const categories = this.dependencies.specificationsOption.getCategories();
        categories.push({ id: newId, name });

        editingElement.dataset.pendingCategoryId = String(newId);
        delete editingElement.dataset.pendingNewCategoryName;
        this.dependencies.specificationsOption.setCategoryCreateMode(false);

        this.dependencies.builderOptions.setNextTarget(editingElement);
    }
}

registry
    .category("website-plugins")
    .add(SpecificationsPlugin.id, SpecificationsPlugin);
