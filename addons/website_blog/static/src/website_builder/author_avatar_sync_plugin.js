import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";

export class AuthorAvatarSyncPlugin extends Plugin {
    static id = "authorAvatarSync";
    static dependencies = ["domReferenceMap"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        /**
         * @param {import("@html_editor/core/dom_observer_plugin").SerializedMutation[]} records
         */
        on_pending_mutations_staged_handlers: (records) => {
            records
                .filter((r) => r.type === "attributes" && r.attributeName === "data-oe-many2one-id")
                .map((r) => ({...r, target: this.dependencies.domReferenceMap.getNodeById(r.nodeId)}))
                .filter((r) => r.target.dataset.oeField === "author_id")
                .forEach((r) => this.authorToUpdate.set(r.target.dataset.oeId, r.value));
        },
        on_pending_mutations_normalized_handlers: () => {
            const toUpdate = this.authorToUpdate;
            this.authorToUpdate = new Map();
            for (const [oeId, id] of toUpdate.entries()) {
                for (const node of this.editable.querySelectorAll(
                    `[data-oe-model="blog.post"][data-oe-id="${oeId}"][data-oe-field="author_avatar"]`
                )) {
                    node.querySelector("img").src = `/web/image/res.partner/${id}/avatar_1024`;
                }
            }
        },
    };

    setup() {
        this.authorToUpdate = new Map();
    }
}

registry.category("website-plugins").add(AuthorAvatarSyncPlugin.id, AuthorAvatarSyncPlugin);
