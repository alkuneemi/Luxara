import { reactive } from "@web/owl2/utils";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ExtraFieldsPlugin extends Plugin {
    static id = "extraFieldsOption";
    static shared = [
        "clearLoadedExtraFields",
        "getExtraFields",
        "getCategories",
        "loadExtraFields",
    ];

    _extraFields = reactive([]);
    _categories = reactive([]);
    _loadedExtraFields = null;

    resources = {
        builder_actions: {
            AddExtraFieldAction,
            CreateCategoryAction,
            DeleteExtraFieldAction,
            ChangeExtraFieldCategoryAction,
        },
    };

    getExtraFields() {
        return this._extraFields;
    }

    getCategories() {
        return this._categories;
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

        delete editingElement.dataset.pendingNewCategoryName;

        editingElement.__onCategoryCreated?.({ id: newId, name });
        delete editingElement.__onCategoryCreated;

        this.dependencies.extraFieldsOption.clearLoadedExtraFields();
    }
}

class DeleteExtraFieldAction extends BuilderAction {
    static id = "deleteExtraField";
    static dependencies = ["extraFieldsOption"];

    setup() {
        this.reload = {};
    }

    async apply({ editingElement }) {
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);
        await this.services.orm.unlink("website.sale.extra.field", [extraFieldId]);
        this.dependencies.extraFieldsOption.clearLoadedExtraFields();
    }
}

class ChangeExtraFieldCategoryAction extends BuilderAction {
    static id = "changeExtraFieldCategory";
    static dependencies = ["extraFieldsOption"];

    setup() {
        this.reload = {};
    }

    async apply({ editingElement }) {
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);
        const categoryId = parseInt(editingElement.dataset.changeExtraFieldCategory) || false;
        delete editingElement.dataset.changeExtraFieldCategory;
        await this.services.orm.write(
            "website.sale.extra.field",
            [extraFieldId],
            { category_id: categoryId }
        );
        this.dependencies.extraFieldsOption.clearLoadedExtraFields();
    }
}

registry.category("website-plugins").add(ExtraFieldsPlugin.id, ExtraFieldsPlugin);
