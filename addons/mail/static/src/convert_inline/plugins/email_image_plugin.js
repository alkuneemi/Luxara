import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { getImageSrc } from "@html_editor/utils/image";
import { loadImage } from "@html_editor/utils/image_processing";

export class EmailImagePlugin extends Plugin {
    static id = "image";
    resources = {
        load_reference_content_handlers: () => this.loadImages(this.config.reference),
    };

    /**
     * Return promises for every image to control when they have their final
     * rendered dimensions.
     * Background images do not influence their content dimensions so they don't
     * have to be waited for.
     */
    loadImages(root) {
        const promises = [];
        for (const img of root.querySelectorAll("img")) {
            const src = getImageSrc(img);
            if (src) {
                promises.push(loadImage(src));
            }
        }
        return Promise.allSettled(promises);
    }

    /**
     * <i>/<span> fa + circle should be centered properly when the icon is converted into an image
     *
     */
    // TODO EGGMAIL: fontToImg
}

registry.category("mail-html-conversion-plugins").add(EmailImagePlugin.id, EmailImagePlugin);
