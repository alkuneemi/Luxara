import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["getModelNameFilter"];
    modelNameFilter = "event.event";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        dynamic_filter_search_domain_processors: (domain, { eventByTagIds }) => {
            if (eventByTagIds) {
                const tagsByCategory = Map.groupBy(eventByTagIds, (tag) => tag.category_id[0]);
                for (const tags of tagsByCategory.values()) {
                    domain.push(["tag_ids", "in", tags.map((e) => e.id)]);
                }
            }
        },
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_event_upcoming_snippet")) {
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter,
                [],
                { limit: 3 }
            );
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);
