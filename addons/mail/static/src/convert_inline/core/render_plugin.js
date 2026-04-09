import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";

export class RenderPlugin extends Plugin {
    static id = "render";
    resources = {
        on_render_email_template_handlers: this.renderEmailHtml.bind(this),
    };

    /**
     * TODO EGGMAIL: move the following in a "render_plugin"
     */

    ensureTemplateContent(template) {
        if (!template.content.firstChild) {
            const paragraph = this.config.referenceDocument.createElement("P");
            const br = this.config.referenceDocument.createElement("BR");
            paragraph.append(br);
            template.content.appendChild(paragraph);
        }
    }

    renderEmailHtml(template) {
        // TODO EGGMAIL: use the LayoutModel tree to render the final email
        this.ensureTemplateContent(template);
    }
}

registry.category("mail-html-conversion-core-plugins").add(RenderPlugin.id, RenderPlugin);
