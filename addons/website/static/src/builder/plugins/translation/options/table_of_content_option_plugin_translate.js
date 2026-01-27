import { Plugin } from "@html_editor/plugin";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { registry } from "@web/core/registry";

export class TranslateTableOfContentOptionPlugin extends Plugin {
    static id = "tableOfContentOption";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        normalize_processors: this.normalize.bind(this),
        content_not_editable_selectors: [".s_table_of_content_navbar"],
    };

    normalize(root) {
        applyFunDependOnSelectorAndExclude(this.updateTableOfContentNavbar.bind(this), root, {
            selector: ".s_table_of_content_main :is(h1, h2, h3, h4, h5, h6)",
        });
    }

    updateTableOfContentNavbar(headingEl) {
        const linkEl = this.document.querySelector(
            `.s_table_of_content_navbar a[href="#${headingEl.id}"]`
        );
        const newText = headingEl.textContent;
        if (linkEl.textContent !== newText) {
            linkEl.textContent = newText;
            const tranlationSpanOfLinkEl = linkEl.closest("[data-oe-translation-state]");
            if (tranlationSpanOfLinkEl) {
                tranlationSpanOfLinkEl.classList.add("o_dirty");
            }
        }
    }
}

registry
    .category("translation-plugins")
    .add(TranslateTableOfContentOptionPlugin.id, TranslateTableOfContentOptionPlugin);
