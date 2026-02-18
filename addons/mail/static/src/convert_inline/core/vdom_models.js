import { uuid } from "@web/core/utils/strings";

/**
 * @property { Node } referenceNode node from this.config.reference
 * @property { Comment } vNode comment node to represent the referenceNode in
 *           another NodeInfo fragment (used to reference childNode position for
 *           the final rendering)
 * @property { DocumentFragment } fragment fragment containing the final
 *           representation of the reference node, and other vNode
 *
 * TODO EGGMAIL better documentation for:
 * renderNode: clone of a vNode during one rendering phase (temporary, disposable)
 * renderFragment: clone of a fragment during one rendering phase (temporary, disposable)
 * templateNode: clone of a referenceNode in its nodeInfo.fragment
 *   (permanent but it may be replaced by something else in the fragment)
 */

export class NodeInfo {
    fragment = undefined;
    hasLayoutStrategy = false;
    isDiscarded = false;
    renderId = uuid();

    constructor({ referenceNode, vNode }) {
        this.referenceNode = referenceNode;
        this.vNode = vNode;
    }

    defineLayoutStrategy({ pluginId, isDiscarded = false } = {}) {
        this.hasLayoutStrategy = true;
        this.isDiscarded = isDiscarded;
        this.pluginId = pluginId;
    }
}
