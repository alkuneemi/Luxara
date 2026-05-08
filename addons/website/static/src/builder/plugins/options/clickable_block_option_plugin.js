import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { setHrefUrl } from "@html_builder/plugins/utils";

export class ClickableBlockOptionPlugin extends Plugin {
    static id = "clickableBlockOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetBlockClickableAction,
            SetBlockAnchorUrlAction,
        },
        is_empty_link_legit_predicates: (linkEl) => {
            if (linkEl.matches("a.stretched-link[href]")) {
                return true;
            }
        },
        can_have_hover_effect_predicates: (el) => this.canHaveHoverEffect(el),
    };

    canHaveHoverEffect(el) {
        // Disable the "onHover" option since they will not be triggered behind
        // the stretched-link overlay.
        return !el.parentElement.closest("*:has(> .stretched-link)");
    }
}

class SetBlockClickableAction extends BuilderAction {
    static id = "setBlockClickable";
    apply({ editingElement }) {
        const anchorEl = document.createElement("a");
        anchorEl.classList.add("stretched-link");
        editingElement.prepend(anchorEl);
    }
    clean({ editingElement }) {
        editingElement.querySelector(":scope > a.stretched-link")?.remove();
    }
    isApplied({ editingElement }) {
        return !!editingElement.querySelector(":scope > a.stretched-link");
    }
}

class SetBlockAnchorUrlAction extends BuilderAction {
    static id = "setBlockAnchorUrl";
    apply({ editingElement, value }) {
        const linkEl = editingElement.querySelector(":scope > a.stretched-link");
        if (linkEl) {
            setHrefUrl(linkEl, value);
        }
    }
    getValue({ editingElement }) {
        const linkEl = editingElement.querySelector(":scope > a.stretched-link");
        return linkEl?.getAttribute("href") || "";
    }
}

registry.category("website-plugins").add(ClickableBlockOptionPlugin.id, ClickableBlockOptionPlugin);
