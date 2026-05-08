import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } DynamicSnippetBlogPostsOptionShared
 * @property { DynamicSnippetBlogPostsOptionPlugin['getModelNameFilter'] } getModelNameFilter
 */

export class DynamicSnippetBlogPostsOptionPlugin extends Plugin {
    static id = "dynamicSnippetBlogPostsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["getModelNameFilter"];
    modelNameFilter = "blog.post";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        dynamic_filter_search_domain_processors: (
            domain,
            { blogByIds, blogByTagIds, blogByAuthorIds }
        ) => {
            if (blogByIds?.length) {
                domain.push(["blog_id", "in", blogByIds.map((e) => e.id)]);
            }
            if (blogByTagIds?.length) {
                domain.push(["tag_ids", "in", blogByTagIds.map((e) => e.id)]);
            }
            if (blogByAuthorIds?.length) {
                domain.push(["author_id", "in", blogByAuthorIds.map((e) => e.id)]);
            }
        },
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_dynamic_snippet_blog_posts")) {
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetBlogPostsOptionPlugin.id, DynamicSnippetBlogPostsOptionPlugin);
