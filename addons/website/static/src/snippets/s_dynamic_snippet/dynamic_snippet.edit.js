import { Interaction } from "@web/public/interaction";
import { DynamicSnippet } from "./dynamic_snippet";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";
import { setElementContent } from "@web/core/utils/html";
import { rewrapDynamicSnippet } from "@website/js/content/wrap_dynamic_snippet";

const DynamicSnippetEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.withSample = true;
        }
        callToAction() {}
    };

registry.category("public.interactions.edit").add("website.dynamic_snippet", {
    Interaction: DynamicSnippet,
    mixin: DynamicSnippetEdit,
});

class DynamicFilterSnippet extends Interaction {
    static selector = ".s_dynamic_snippet_content[data-oe-dynamic-filter-snippet]";

    async willStart() {
        const mainObject = this.services.website_page.mainObject;
        this.content = markup(
            await this.services.http.get(
                `/website/snippet/filter_snippet?params=${encodeURIComponent(
                    this.el.getAttribute("data-oe-dynamic-filter-snippet")
                )}&main_object_name=${mainObject.model}&main_object_id=${mainObject.id}`,
                "text"
            )
        );
    }

    start() {
        setElementContent(this.el, this.content);
        rewrapDynamicSnippet(this.el);
        this.services["public.interactions"].startInteractions(this.el);
    }
}

registry.category("public.interactions.edit").add("website.dynamic_filter_snippet", {
    Interaction: DynamicFilterSnippet,
});
