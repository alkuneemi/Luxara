import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteSetupEditorPlugin extends Plugin {
    static id = "website_setup_editor_plugin";
    resources = {
        before_setup_editor_handlers: this.injectMissingSnippetNames.bind(this),
    };
    /**
     * Ensures snippets have a `data-name` when not added via the snippet dialog
     * (e.g. via configurator or template-generated pages).
     */
    injectMissingSnippetNames() {
        for (const snippetEl of this.editable.querySelectorAll("[data-snippet]:not([data-name])")) {
            const snippetInfo = this.config.snippetModel.getOriginalSnippet(
                snippetEl.dataset.snippet
            );
            if (snippetInfo?.title) {
                snippetEl.dataset.name = snippetInfo.title;
            }
        }
    }
}

registry.category("website-plugins").add(WebsiteSetupEditorPlugin.id, WebsiteSetupEditorPlugin);
