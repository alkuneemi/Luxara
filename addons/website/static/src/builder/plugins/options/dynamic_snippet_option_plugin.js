import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Cache } from "@web/core/utils/cache";
import { BuilderAction } from "@html_builder/core/builder_action";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { omit } from "@web/core/utils/objects";

/**
 * @typedef {object} Template
 * @property {number} id
 * @property {string} name
 * @property {string} columnClasses
 * @property {string} containerClasses
 * @property {string} contentClasses
 * @property {string} extraClasses
 * @property {string} extraSnippetClasses
 * @property {string} key
 * @property {string} numberOfElements
 * @property {string} numberOfElementsSmallDevices
 * @property {string} limit
 * @property {string} rowPerSlide
 * @property {string} thumb
 *
 * @typedef {Object} Filter
 * @property {number} id
 * @property {string} name
 * @property {number} limit
 * @property {string} model_name
 * @property {string} help
 *
 * @typedef {Object} DynamicFilterSnippetParameters
 * @property {string} content_template_key
 * @property {Object} content_extra_data
 * @property {string} wrapper_template_key
 * @property {Object} wrapper_extra_data
 * @property {number} filter_id
 * @property {string} res_model
 * @property {number} res_id
 * @property {Array} search_domain
 * @property {Object} search_domain_extra
 * @property {number} limit
 */

/**
 * @typedef { Object } DynamicSnippetOptionShared
 * @property { DynamicSnippetOptionPlugin['fetchDynamicFilters'] } fetchDynamicFilters
 * @property { DynamicSnippetOptionPlugin['fetchDynamicSnippetTemplates'] } fetchDynamicSnippetTemplates
 * @property { DynamicSnippetOptionPlugin['getDefaultSnippetFilterId'] } getDefaultSnippetFilterId
 * @property { DynamicSnippetOptionPlugin['getDefaultSnippetRecordId'] } getDefaultSnippetRecordId
 * @property { DynamicSnippetOptionPlugin['getDefaultSnippetTemplate'] } getDefaultSnippetTemplate
 * @property { DynamicSnippetOptionPlugin['getSnippetModelName'] } getSnippetModelName
 * @property { DynamicSnippetOptionPlugin['getSnippetTitleClasses'] } getSnippetTitleClasses
 * @property { DynamicSnippetOptionPlugin['getTemplateByKey'] } getTemplateByKey
 * @property { DynamicSnippetOptionPlugin['isModelSnippetTemplate'] } isModelSnippetTemplate
 * @property { DynamicSnippetOptionPlugin['isSingleModeSnippet'] } isSingleModeSnippet
 * @property { DynamicSnippetOptionPlugin['isSingleModeSnippetTemplate'] } isSingleModeSnippetTemplate
 * @property { DynamicSnippetOptionPlugin['setOptionsDefaultValues'] } setOptionsDefaultValues
 * @property { DynamicSnippetOptionPlugin['updateTemplate'] } updateTemplate
 * @property { DynamicSnippetOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

/**
 * @typedef {((domain: import("@web/core/domain").DomainListRepr, domainInfo: Object) => domain)[]} dynamic_filter_search_domain_processors
 */

export const CONTAINER_CLASSES = ["container", "container-fluid", "o_container_small"];

export class DynamicSnippetOptionPlugin extends Plugin {
    static id = "dynamicSnippetOption";
    static shared = [
        "fetchDynamicFilters",
        "fetchDynamicSnippetTemplates",
        "getDefaultSnippetFilterId",
        "getDefaultSnippetRecordId",
        "getDefaultSnippetTemplate",
        "getSnippetModelName",
        "getSnippetTitleClasses",
        "getTemplateByKey",
        "isModelSnippetTemplate",
        "isSingleModeSnippet",
        "isSingleModeSnippetTemplate",
        "setOptionsDefaultValues",
        "updateTemplate",
        "getModelNameFilter",
    ];
    modelNameFilter = "";
    /** @type {Filter[]} */
    fetchedDynamicFilters = [];
    /** @type {Template[]} */
    fetchedDynamicFilterTemplates = [];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            DynamicFilterAction,
            DynamicSnippetTemplateAction,
            DynamicModelAction,
            DynamicRecordAction,
            CustomizeTemplateAction,
            NumberOfRecordsAction,
            DynamicSearchDomainJsonAction,
            DynamicSearchDomainAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_cloned_handlers: ({ cloneEl }) => this.assignUniqueID(cloneEl),
        is_unremovable_selectors: ".s_dynamic_snippet_title",
        dynamic_snippet_wrapper_templates_with_single_mode:
            "website.s_dynamic_snippet_wrapper_grid",
    };
    setup() {
        this.dynamicFiltersCache = new Cache(this._fetchDynamicFilters, JSON.stringify);
        this.dynamicFilterTemplatesCache = new Cache(
            this._fetchDynamicSnippetTemplates,
            JSON.stringify
        );
    }
    destroy() {
        super.destroy();
        this.dynamicFiltersCache.invalidate();
        this.dynamicFilterTemplatesCache.invalidate();
    }
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet")) {
            await this.setOptionsDefaultValues(snippetEl, this.modelNameFilter);
        }
        this.assignUniqueID(snippetEl);
    }
    assignUniqueID(snippetEl) {
        const dynamicEl = snippetEl.querySelector("[data-oe-dynamic-filter-snippet]");
        if (!dynamicEl) {
            return;
        }
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        dynamicParams.wrapper_extra_data ??= {};
        dynamicParams.wrapper_extra_data.unique_id = `sDynamicSnippet${Date.now()}`;
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }

    /**
     * @param {HTMLElement} snippetEl
     * @param {String} modelNameFilter
     * @param {*} [contextualFilterDomain=[]]
     * @param {DynamicFilterSnippetParameters} [extraDefaults={}]
     */
    async setOptionsDefaultValues(
        snippetEl,
        modelNameFilter,
        contextualFilterDomain = [],
        extraDefaults = {}
    ) {
        await this.fetchDynamicFilters({
            model_name: modelNameFilter,
            search_domain: contextualFilterDomain,
        });
        await this.fetchDynamicSnippetTemplates(modelNameFilter);

        /** @type {Object<string, Filter>} */
        const dynamicFilters = {};
        for (const dynamicFilter of this.fetchedDynamicFilters) {
            dynamicFilters[dynamicFilter.id] = dynamicFilter;
        }
        /** @type {Object<string, Template>} */
        const dynamicFilterTemplates = {};
        for (const dynamicFilterTemplate of this.fetchedDynamicFilterTemplates) {
            dynamicFilterTemplates[dynamicFilterTemplate.key] = dynamicFilterTemplate;
        }
        const dynamicEl = snippetEl.querySelector("[data-oe-dynamic-filter-snippet]");
        /** @type {DynamicFilterSnippetParameters} */
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);

        dynamicParams.content_extra_data ??= {};
        Object.assign(dynamicParams.content_extra_data, extraDefaults.content_extra_data);
        dynamicParams.wrapper_extra_data ??= {};
        Object.assign(dynamicParams.wrapper_extra_data, extraDefaults.wrapper_extra_data);
        Object.assign(dynamicParams, omit(extraDefaults, ...Object.keys(dynamicParams)));
        dynamicParams.search_domain_extra ??= {};

        const defaultModelName = modelNameFilter || this.fetchedDynamicFilters[0]?.model_name;
        const isSingleMode = this.isSingleModeSnippet({
            ...dynamicParams,
            res_model: defaultModelName,
        });
        // The snippet simply gets its template from a "template class"
        // when provided. Otherwise, it will use a default template.
        let defaultTemplate = this.fetchedDynamicFilterTemplates.find((template) =>
            snippetEl.classList.contains(this.getTemplateClass(template.key))
        );
        if (!defaultTemplate) {
            defaultTemplate = this.getDefaultSnippetTemplate(defaultModelName, isSingleMode);
        }
        if (isSingleMode) {
            if (defaultModelName) {
                dynamicParams.res_model ??= defaultModelName;
            }
            const defaultSnippetRecordId = await this.getDefaultSnippetRecordId(defaultModelName);
            if (defaultSnippetRecordId) {
                dynamicParams.res_id ??= defaultSnippetRecordId;
            }
            dynamicParams.content_template_key ??= defaultTemplate.key;
            this.updateTemplate(snippetEl, dynamicEl, dynamicParams, defaultTemplate);
        } else {
            let selectedFilterId = dynamicParams.filter_id;
            if (Object.keys(dynamicFilters).length > 0) {
                dynamicParams.limit ??= this.fetchedDynamicFilters[0].limit;
                const defaultFilterId = this.fetchedDynamicFilters[0].id;
                if (!dynamicFilters[selectedFilterId]) {
                    dynamicParams.filter_id = defaultFilterId;
                    selectedFilterId = defaultFilterId;
                }
            }
            if (
                dynamicFilters[selectedFilterId] &&
                !dynamicFilterTemplates[dynamicParams.content_template_key]
            ) {
                dynamicParams.content_template_key = defaultTemplate.key;
                this.updateTemplate(snippetEl, dynamicEl, dynamicParams, defaultTemplate);
            }
        }
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }
    getTemplateByKey(templateKey) {
        return (
            templateKey && this.fetchedDynamicFilterTemplates.find(({ key }) => key === templateKey)
        );
    }
    getTemplateClass(templateKey) {
        return templateKey.replace(/.*\.dynamic_filter_template_/, "s_");
    }
    /**
     * Updates the `snippetEl`, `dynamicEl` and `dynamicParams` to correspond to a new `template`
     *
     * @param {HTMLElement} snippetEl
     * @param {HTMLElement} dynamicEl
     * @param {DynamicFilterSnippetParameters} dynamicParams
     * @param {Template} template
     */
    updateTemplate(snippetEl, dynamicEl, dynamicParams, template) {
        const newTemplateKey = template.key;
        const oldTemplateKey = dynamicParams.content_template_key;
        const oldTemplate = this.getTemplateByKey(oldTemplateKey);
        dynamicParams.content_template_key = newTemplateKey;
        if (oldTemplateKey) {
            snippetEl.classList.remove(this.getTemplateClass(oldTemplateKey));
        }
        snippetEl.classList.add(this.getTemplateClass(newTemplateKey));

        dynamicParams.wrapper_extra_data ??= {};
        if (template.numberOfElements) {
            dynamicParams.wrapper_extra_data.number_of_elements = template.numberOfElements;
        } else {
            delete dynamicParams.wrapper_extra_data.number_of_elements;
        }
        if (template.numberOfElementsSmallDevices) {
            dynamicParams.wrapper_extra_data.number_of_elements_small_devices =
                template.numberOfElementsSmallDevices;
        } else {
            delete dynamicParams.wrapper_extra_data.number_of_elements_small_devices;
        }
        if (template.limit) {
            dynamicParams.limit = template.limit;
        }
        if (template.extraClasses) {
            dynamicParams.wrapper_extra_data.extra_classes = template.extraClasses;
        } else {
            delete dynamicParams.wrapper_extra_data.extra_classes;
        }
        if (template.columnClasses) {
            dynamicParams.wrapper_extra_data.column_classes = template.columnClasses;
        } else {
            delete dynamicParams.wrapper_extra_data.column_classes;
        }
        if (oldTemplate) {
            const snippetContainerEl = snippetEl.querySelector(".s_dynamic_snippet_container");
            snippetContainerEl.classList.remove(...CONTAINER_CLASSES);
            snippetContainerEl.classList.add(
                ...(template.containerClasses || "container").split(" ")
            );

            dynamicEl.classList.remove(...(oldTemplate.contentClasses?.split(" ") || []));
            dynamicEl.classList.add(...(template.contentClasses?.split(" ") || []));

            snippetEl.classList.remove(...(oldTemplate.extraSnippetClasses?.split(" ") || []));
            snippetEl.classList.add(...(template.extraSnippetClasses?.split(" ") || []));
        }
    }
    async fetchDynamicFilters(params) {
        this.fetchedDynamicFilters = await this.dynamicFiltersCache.read(params);
        return this.fetchedDynamicFilters;
    }
    async _fetchDynamicFilters(params) {
        return rpc("/website/snippet/options_filters", params);
    }
    async fetchDynamicSnippetTemplates(modelName) {
        this.fetchedDynamicFilterTemplates = await this.dynamicFilterTemplatesCache.read({
            filter_name: modelName.replaceAll(".", "_"),
        });
        return this.fetchedDynamicFilterTemplates;
    }
    async _fetchDynamicSnippetTemplates(params) {
        return rpc("/website/snippet/filter_templates", params);
    }
    /**
     * @param {DynamicFilterSnippetParameters} params
     * @returns {boolean}
     */
    isSingleModeSnippet(params) {
        // TODO: Currently, we need to verify that at least one template is
        // available for single record mode to be enabled. This check should be
        // removed once all single record templates have been added.
        return !!(
            params.limit === 1 &&
            this.getDefaultSnippetTemplate(this.getSnippetModelName(params), true) &&
            this.getResource("dynamic_snippet_wrapper_templates_with_single_mode").includes(
                params.wrapper_template_key
            )
        );
    }
    isSingleModeSnippetTemplate(key) {
        return key.includes("_single_");
    }
    isModelSnippetTemplate(key, modelName) {
        return modelName && key.includes(`_${modelName.replaceAll(".", "_")}_`);
    }
    getDefaultSnippetTemplate(modelName, singleMode) {
        if (modelName) {
            // Return the default snippet template associated with the current
            // model for either single or multi-record modes.
            return this.fetchedDynamicFilterTemplates.find((template) => {
                const isSingleTemplate = this.isSingleModeSnippetTemplate(template.key);
                return (
                    this.isModelSnippetTemplate(template.key, modelName) &&
                    (singleMode ? isSingleTemplate : !isSingleTemplate)
                );
            });
        }
    }
    async getDefaultSnippetRecordId(modelName) {
        const defaultRecrod = await this.services.orm.searchRead(
            modelName,
            [["is_published", "=", true]],
            ["id"],
            { limit: 1 }
        );
        return defaultRecrod[0]?.id || "";
    }
    getDefaultSnippetFilterId(modelName) {
        return this.fetchedDynamicFilters.find(({ model_name }) => model_name === modelName).id;
    }
    getSnippetModelName({ res_model, filter_id }) {
        return (
            res_model || this.fetchedDynamicFilters.find(({ id }) => id === filter_id)?.model_name
        );
    }
    getSnippetTitleClasses(position) {
        const classes = {
            left: "d-flex justify-content-between s_dynamic_snippet_title_aside col-lg-3 flex-lg-column justify-content-lg-start",
            top: "d-flex justify-content-between",
            none: "d-none",
        };
        return position ? classes[position] : classes;
    }
}

export class DynamicSnippetParamsAction extends BuilderAction {
    isApplied(args) {
        const dynamicEl = args.editingElement.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        return this.isAppliedInParams({ ...args, dynamicEl, dynamicParams });
    }
    getValue(args) {
        const dynamicEl = args.editingElement.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        return this.getValueInParams({ ...args, dynamicEl, dynamicParams });
    }
    apply(args) {
        const dynamicEl = args.editingElement.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        this.applyInParams({ ...args, dynamicEl, dynamicParams });
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }
    clean(args) {
        const dynamicEl = args.editingElement.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        this.cleanInParams({ ...args, dynamicEl, dynamicParams });
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }
}

export class DynamicFilterAction extends BuilderAction {
    static id = "dynamicFilter";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        return JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet).filter_id === params.id;
    }
    async apply({ editingElement: el, params }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        const utils = this.dependencies.dynamicSnippetOption;
        let defaultTemplate = params.defaultTemplate;
        dynamicParams.filter_id = params.id;
        // Only if filter's model name changed
        if (
            !dynamicParams.content_template_key ||
            !utils.isModelSnippetTemplate(dynamicParams.content_template_key, params.model_name)
        ) {
            if (utils.isSingleModeSnippet(dynamicParams)) {
                dynamicParams.res_model = params.model_name;
                delete dynamicParams.filter_id;
                defaultTemplate = utils.getDefaultSnippetTemplate(params.model_name, true);
                dynamicParams.res_id = await utils.getDefaultSnippetRecordId(params.model_name);
            }
            utils.updateTemplate(el, dynamicEl, dynamicParams, defaultTemplate);
        }
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }
}
export class DynamicSnippetTemplateAction extends BuilderAction {
    static id = "dynamicSnippetTemplate";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        return dynamicParams.content_template_key === params.key;
    }
    apply({ editingElement: el, params }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        this.dependencies.dynamicSnippetOption.updateTemplate(el, dynamicEl, dynamicParams, params);
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }
}
export class CustomizeTemplateAction extends DynamicSnippetParamsAction {
    static id = "customizeTemplate";
    isAppliedInParams({ dynamicParams, params: { mainParam: customDataKey } }) {
        return dynamicParams.content_extra_data[customDataKey];
    }
    applyInParams({ dynamicParams, params: { mainParam: customDataKey } }) {
        dynamicParams.content_extra_data[customDataKey] = true;
    }
    cleanInParams({ dynamicParams, params: { mainParam: customDataKey } }) {
        dynamicParams.content_extra_data[customDataKey] = false;
    }
}
export class DynamicModelAction extends BuilderAction {
    static id = "dynamicModel";
    static dependencies = ["dynamicSnippetOption"];
    isApplied({ editingElement: el, params }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        return dynamicParams.res_model === params.mainParam;
    }
    async apply({ editingElement: el, params: { mainParam: modelName } }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        const utils = this.dependencies.dynamicSnippetOption;
        // Update the snippet data attributes (only available in the
        // "single record" mode).
        if (dynamicParams.res_model !== modelName) {
            dynamicParams.res_model = modelName;
            dynamicParams.res_id = await utils.getDefaultSnippetRecordId(modelName);
            utils.updateTemplate(
                el,
                dynamicEl,
                dynamicParams,
                utils.getDefaultSnippetTemplate(modelName, true)
            );
            dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
        }
    }
}
export class DynamicRecordAction extends DynamicSnippetParamsAction {
    static id = "dynamicRecord";
    getValueInParams({ dynamicParams }) {
        if (dynamicParams.res_id) {
            return JSON.stringify({ id: parseInt(dynamicParams.res_id) });
        }
    }
    applyInParams({ dynamicParams, value }) {
        const { id } = JSON.parse(value);
        dynamicParams.res_id = id;
    }
}
export class NumberOfRecordsAction extends BuilderAction {
    static id = "numberOfRecords";
    static dependencies = ["dynamicSnippetOption", "builderActions"];

    setup() {
        this.previousTemplate = false;
        this.utils = this.dependencies.dynamicSnippetOption;
    }
    async load({ editingElement }) {
        const dynamicEl = editingElement.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        const modelName = this.utils.getSnippetModelName(dynamicParams);
        return {
            modelName,
            defaultRecordId: await this.utils.getDefaultSnippetRecordId(modelName),
        };
    }
    isApplied({ editingElement: el, params }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        return dynamicParams.limit === params.mainParam;
    }
    apply({ editingElement: el, params, loadResult }) {
        const dynamicEl = el.querySelector("[data-oe-dynamic-filter-snippet]");
        const dynamicParams = JSON.parse(dynamicEl.dataset.oeDynamicFilterSnippet);
        const isSingleModeBefore = this.utils.isSingleModeSnippet(dynamicParams);
        dynamicParams.limit = params.mainParam;
        // Changing the number of records should automatically switch to a
        // "single record" filter mode if only one record is selected, and
        // conversely, revert to the default filter mode when more than one
        // record is selected.
        const isSingleModeAfter = this.utils.isSingleModeSnippet(dynamicParams);
        const switchMode = isSingleModeBefore !== isSingleModeAfter;
        if (switchMode) {
            const canUsePreviousTemplate =
                !!this.previousTemplate &&
                this.utils.isModelSnippetTemplate(
                    this.previousTemplate.key,
                    loadResult.modelName
                ) &&
                !!this.utils.isSingleModeSnippetTemplate(this.previousTemplate.key) ===
                    isSingleModeAfter;
            const newModeDefaultTemplate = !canUsePreviousTemplate
                ? this.utils.getDefaultSnippetTemplate(loadResult.modelName, isSingleModeAfter)
                : this.previousTemplate;
            this.previousTemplate = this.utils.getTemplateByKey(dynamicParams.content_template_key);
            if (isSingleModeAfter) {
                // Remove useless data on the target and set the single
                // record default values.
                delete dynamicParams.filter_id;
                dynamicParams.res_model = loadResult.modelName;
                dynamicParams.res_id = loadResult.defaultRecordId;
            } else {
                dynamicParams.filter_id = this.utils.getDefaultSnippetFilterId(
                    loadResult.modelName
                );
                delete dynamicParams.res_model;
                delete dynamicParams.res_id;
            }
            // Update the snippet title section.
            const titleEl = el.querySelector(".s_dynamic_snippet_title");
            const classAction = this.dependencies.builderActions.getAction("classAction");
            const titleClasses = Object.values(this.utils.getSnippetTitleClasses()).find(
                (classes) =>
                    titleEl.matches(
                        classes
                            .split(" ")
                            .map((c) => "." + c)
                            .join("")
                    )
            );
            classAction.clean({
                editingElement: titleEl,
                params: { mainParam: titleClasses },
            });
            classAction.apply({
                editingElement: titleEl,
                params: {
                    mainParam: this.utils.getSnippetTitleClasses(
                        isSingleModeAfter ? "none" : "top"
                    ),
                },
            });
            this.utils.updateTemplate(el, dynamicEl, dynamicParams, newModeDefaultTemplate);
        }
        dynamicEl.dataset.oeDynamicFilterSnippet = JSON.stringify(dynamicParams);
    }
}

export class DynamicSearchDomainAction extends DynamicSnippetParamsAction {
    static id = "dynamicSearchDomain";
    getValueInParams({ dynamicEl, params: { mainParam: key } }) {
        if (dynamicEl.dataset.searchDomainInfo) {
            return JSON.parse(dynamicEl.dataset.searchDomainInfo)?.[key];
        }
    }
    applyInParams({ dynamicEl, dynamicParams, params: { mainParam: key }, value }) {
        const searchDomainInfo = dynamicEl.dataset.searchDomainInfo
            ? JSON.parse(dynamicEl.dataset.searchDomainInfo)
            : {};
        searchDomainInfo[key] = value;
        dynamicEl.dataset.searchDomainInfo = JSON.stringify(searchDomainInfo);
        dynamicParams.search_domain = this.processThrough(
            "dynamic_filter_search_domain_processors",
            [],
            searchDomainInfo
        );
    }
}

export class DynamicSearchDomainJsonAction extends DynamicSearchDomainAction {
    static id = "dynamicSearchDomainJson";
    getValueInParams(args) {
        const searchDomainInfoValue = super.getValueInParams(args);
        return searchDomainInfoValue && JSON.stringify(searchDomainInfoValue);
    }
    applyInParams(args) {
        super.applyInParams({ ...args, value: JSON.parse(args.value) });
    }
}

registry.category("website-plugins").add(DynamicSnippetOptionPlugin.id, DynamicSnippetOptionPlugin);

class DynamicFilterSnippetPlugin extends Plugin {
    static id = "dynamicFilterSnippet";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        clean_for_save_processors: (root) => {
            for (const dynamicEl of selectElements(root, "[data-oe-dynamic-filter-snippet]")) {
                // This mirrors the handling of `t-dynamic-filter-snippet`
                // during qweb rendering server side. The information stored
                // in the directive were stored in `data-oe-dynamic-filter-snippet`
                // for the browser side to use. This code re-creates the
                // directive. (and remove the dynamic content)
                dynamicEl.replaceChildren();
                const params = dynamicEl.getAttribute("data-oe-dynamic-filter-snippet");
                dynamicEl.removeAttribute("data-oe-dynamic-filter-snippet");
                dynamicEl.setAttribute("t-dynamic-filter-snippet", params);
            }
        },
    };
}

registry.category("website-plugins").add(DynamicFilterSnippetPlugin.id, DynamicFilterSnippetPlugin);
