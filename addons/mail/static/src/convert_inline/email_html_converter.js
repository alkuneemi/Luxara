import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { PluginManager } from "./plugin_manager";

export class EmailHtmlConverter extends PluginManager {
    /**
     * @param {MailHtmlConversionConfig} config
     */
    async convertToEmailHtml(config) {
        if (this.isDestroyed) {
            return;
        }
        this.setup();
        this.config = config;

        this.preparePlugins();
        this.startPlugins();
        this.config.updateLayoutDimensions();
        // TODO EGGMAIL: add preProcessCallbacks inside a plugin, exclusive to
        // mass_mailing
        for (const cb of config.preProcessCallbacks ?? []) {
            cb(config.reference);
        }
        this.isReady = true;

        // const inlineTemplate = await this.htmlConversion();
        // if (!inlineTemplate) {
        //     return null;
        // }

        // Old toInline
        // TODO EGGMAIL: adapt usage, use plugin instead of old method
        const cssRules = getCSSRules(this.config.referenceDocument);
        await toInline(this.config.reference, cssRules);
        return this.config.reference.innerHTML;

        // return inlineTemplate.innerHTML;
    }

    getEmailTemplate() {
        const template = this.config.referenceDocument.createElement("TEMPLATE");
        this.trigger("render_email_html_handlers", template);
        // TODO EGGMAIL: post-process the template, or try to keep all the work before template generation?
        return template;
    }

    async htmlConversion() {
        // 1 load async content (i.e. image) for final dimensions
        await Promise.all(
            this.getResource("load_reference_content_handlers")
                .map((job) => job())
                .flat()
        );
        if (this.isDestroyed) {
            return null;
        }
        // 2 notify plugins that the reference is ready to be used as such (e.g. for style computations)
        this.trigger("reference_content_loaded_handlers");

        const emailTemplate = this.getEmailTemplate();

        return emailTemplate;
    }

    onLayoutDimensionsUpdate({ width, height }) {
        this.trigger("update_layout_dimensions_handlers", { width, height });
    }
}
