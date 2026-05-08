import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { WebsiteBackgroundOption } from "@website/builder/plugins/options/background_option";
import { registry } from "@web/core/registry";

export class ServicesPackItemOption extends BaseOptionComponent {
    static id = "services_pack_item_option";
    static template = "website.ServicesPackItemOption";
    static components = {
        WebsiteBackgroundOption,
    };
}

registry.category("website-options").add(ServicesPackItemOption.id, ServicesPackItemOption);

