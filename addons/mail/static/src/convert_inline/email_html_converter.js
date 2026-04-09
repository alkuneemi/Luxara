// import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { PluginManager } from "./plugin_manager";

export class EmailHtmlConverter extends PluginManager {
    /**
     * @param {MailHtmlConversionConfig} config
     */
    async convertToEmailHtml(config) {
        if (this.isDestroyed) {
            return null;
        }
        this.setup();
        this.config = config;

        this.preparePlugins();
        this.startPlugins();
        this.isReady = true;

        const inlineTemplate = await this.htmlConversion();
        if (!inlineTemplate) {
            return null;
        }
        return inlineTemplate.innerHTML;

        // // Old toInline
        // // TODO EGGMAIL: adapt usage, use plugin instead of old method
        // const cssRules = getCSSRules(this.config.referenceDocument);
        // await toInline(this.config.reference, cssRules);
        // return this.config.reference.innerHTML;
    }

    /**
     * Can be called multiple times to render new copies
     *
     * @returns {HTMLTemplateElement}
     */
    renderEmailTemplate() {
        const template = this.config.referenceDocument.createElement("TEMPLATE");
        if (this.canRenderEmailTemplate) {
            this.trigger("on_render_email_template_handlers", template);
        }
        return template;
    }

    async htmlConversion() {
        // 1 prepare working environment, this is the only phase where reference
        // can be modified
        this.trigger("on_will_load_reference_content_handlers");

        // 2 load async content (e.g. images) for final dimensions
        await Promise.all(this.trigger("on_load_reference_content_handlers").flat());
        if (this.isDestroyed) {
            return null;
        }
        // 3 notify plugins that the reference is ready to be used as such (e.g. for style computations)
        this.trigger("on_reference_content_loaded_handlers");

        // 4 build the analysis tree (discard/absorb/annotate reference nodes)
        this.trigger("on_build_analysis_tree_handlers");

        // 5 build the render tree (from analysis constraints)
        this.trigger("on_build_render_tree_handlers");

        this.canRenderEmailTemplate = true;
        // 6 render the email template from the render tree
        return this.renderEmailTemplate();
    }

    onLayoutDimensionsUpdated(dimensions) {
        this.trigger("on_layout_dimensions_updated_handlers", dimensions);
    }
}
