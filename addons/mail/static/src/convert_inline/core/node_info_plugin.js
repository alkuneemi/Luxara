import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { NodeInfo } from "./node_models";

const ALLOWED_NODE_TYPES = [Node.ELEMENT_NODE, Node.TEXT_NODE];

export class NodeInfoPlugin extends Plugin {
    static id = "nodeInfo";
    static shared = [
        "createReferenceTreeWalker",
        "getNodeInfo",
        "isAllowedReferenceNode",
        "processChildNodes",
    ];

    setup() {
        this.referenceToInfo = new WeakMap();
    }

    processChildNodes(node, callback = () => {}) {
        const nodes = [];
        let child = node.firstChild;
        while (child) {
            const currentChild = child;
            child = child.nextSibling;
            if (!this.isAllowedReferenceNode(currentChild)) {
                continue;
            }
            if (callback(currentChild) !== false) {
                nodes.push(currentChild);
            }
        }
        return nodes;
    }

    isAllowedReferenceNode(node) {
        return ALLOWED_NODE_TYPES.includes(node.nodeType);
    }

    /**
     * Get nodeInfo related to a reference node or its related vNode.
     *
     * @param {Node} node referenceNode or vNode
     * @returns {NodeInfo} nodeInfo
     */
    getNodeInfo(node) {
        let nodeInfo;
        if (this.config.referenceDocument.contains(node)) {
            nodeInfo = this.referenceToInfo.get(node);
            if (!nodeInfo) {
                nodeInfo = new NodeInfo({ referenceNode: node });
                this.referenceToInfo.set(node, nodeInfo);
            }
        }
        if (!nodeInfo) {
            // TODO EGGMAIL: error handling
            throw new Error(
                "The provided node can not be associated with an emailHtmlConversion nodeInfo."
            );
        }
        return nodeInfo;
    }

    createReferenceTreeWalker(filter = () => NodeFilter.FILTER_ACCEPT) {
        return this.config.referenceDocument.createTreeWalker(
            this.config.reference,
            NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
            filter
        );
    }
}

registry.category("mail-html-conversion-core-plugins").add(NodeInfoPlugin.id, NodeInfoPlugin);
