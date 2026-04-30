import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ServicesPackOptionPlugin extends Plugin {
    static id = "servicesPackOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        mark_color_level_selector_params: [
            { selector: ".s_services_pack_item", applyTo: ":scope > .row" },
        ],
    };
}

registry.category("website-plugins").add(ServicesPackOptionPlugin.id, ServicesPackOptionPlugin);

