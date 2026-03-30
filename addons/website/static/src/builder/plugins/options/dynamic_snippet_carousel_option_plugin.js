import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DynamicSnippetParamsAction } from "./dynamic_snippet_option_plugin";

/**
 * @typedef { Object } DynamicSnippetCarouselOptionShared
 * @property { DynamicSnippetCarouselOptionPlugin['setOptionsDefaultValues'] } setOptionsDefaultValues
 * @property { DynamicSnippetCarouselOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

export class DynamicSnippetCarouselOptionPlugin extends Plugin {
    static id = "dynamicSnippetCarouselOption";
    static shared = ["setOptionsDefaultValues", "getModelNameFilter"];
    static dependencies = ["dynamicSnippetOption"];
    modelNameFilter = "";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetCarouselSliderSpeedAction,
            DynamicCarouselScrollModeAction,
        },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_carousel")) {
            await this.setOptionsDefaultValues(snippetEl, this.modelNameFilter);
        }
    }
    async setOptionsDefaultValues(
        snippetEl,
        modelNameFilter,
        contextualFilterDomain = [],
        extraDefaults = {}
    ) {
        await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
            snippetEl,
            modelNameFilter,
            contextualFilterDomain,
            {
                ...extraDefaults,
                wrapper_extra_data: {
                    carousel_interval: 5000,
                    ...extraDefaults.wrapper_extra_data,
                },
            }
        );
    }
}

export class SetCarouselSliderSpeedAction extends DynamicSnippetParamsAction {
    static id = "setCarouselSliderSpeed";
    getValueInParams({ dynamicParams }) {
        return dynamicParams.wrapper_extra_data.carousel_interval === undefined
            ? undefined
            : dynamicParams.wrapper_extra_data.carousel_interval / 1000;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.wrapper_extra_data.carousel_interval = value * 1000;
    }
}

export class DynamicCarouselScrollModeAction extends DynamicSnippetParamsAction {
    static id = "dynamicCarouselScrollMode";
    isAppliedInParams({ dynamicParams, value }) {
        return dynamicParams.wrapper_extra_data.scroll_mode === value;
    }
    applyInParams({ dynamicParams, value }) {
        dynamicParams.wrapper_extra_data.scroll_mode = value;
    }
    cleanInParams({ dynamicParams }) {
        delete dynamicParams.wrapper_extra_data.scroll_mode;
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetCarouselOptionPlugin.id, DynamicSnippetCarouselOptionPlugin);
