import { Plugin } from "@html_editor/plugin";
import { descendants } from "@html_editor/utils/dom_traversal";

/**
 * @typedef { string } NodeId
 *
 * @typedef { Object } Tree
 * @property { Node } node
 * @property { Tree[] } children
 *
 * @typedef { Object } SerializedNode
 * @property { number } nodeType
 * @property { NodeId } nodeId
 * @property { string } textValue
 * @property { string } tagName
 * @property { SerializedNode[] } children
 * @property { Record<string, string> } attributes
 */

/**
 * @typedef { Object } DomReferenceMapShared
 * @property { DomReferenceMapPlugin['reset'] } reset
 * @property { DomReferenceMapPlugin['hasNode'] } hasNode
 * @property { DomReferenceMapPlugin['register'] } register
 * @property { DomReferenceMapPlugin['set'] } set
 * @property { DomReferenceMapPlugin['getNodeById'] } getNodeById
 * @property { DomReferenceMapPlugin['getNodeId'] } getNodeId
 * @property { DomReferenceMapPlugin['serializeTree'] } serializeTree
 * @property { DomReferenceMapPlugin['unserializeNode'] } unserializeNode
 */
export class DomReferenceMapPlugin extends Plugin {
    static id = "domReferenceMap";
    static dependencies = ["sanitize"];
    static shared = [
        "reset",
        "hasNode",
        "register",
        "set",
        "getNodeById",
        "getNodeId",
        "serializeTree",
        "unserializeNode",
    ];
    resources = {
        on_will_reset_history_handlers: this.reset.bind(this),
    };

    setup() {
        this.reset();
    }

    reset() {
        // Private properties enclosed in the constructor
        /** @type {Map<string, Node>} */
        this.idToNodeMap = new Map();
        /** @type {Map<Node, string>} */
        this.nodeToIdMap = new Map();
        this.register(this.editable);
    }

    /**
     * @param { Node } node
     * @returns { boolean }
     */
    hasNode(node) {
        return this.nodeToIdMap.has(node);
    }

    /**
     * @param { Node } node
     * @param { boolean } [setDescendentsIds = true] @todo  see if we can get
     *                                                      rid of this argument
     * @returns { NodeId }
     */
    register(node, setDescendentsIds = true) {
        let id = this.getNodeId(node);
        if (!id) {
            id = node === this.editable ? "root" : this.generateId();
            this.set(id, node);
            if (setDescendentsIds) {
                node = node.firstChild;
                while (node) {
                    this.register(node);
                    node = node.nextSibling;
                }
            }
        }
        return id;
    }

    /**
     * @param { NodeId } id
     * @param { Node } node
     */
    set(id, node) {
        if (!id || !node) {
            throw new Error("Id and Node cannot be nullish");
        }
        // Remove old mappings
        const oldNode = this.idToNodeMap.get(id);
        this.nodeToIdMap.delete(oldNode);
        const oldId = this.nodeToIdMap.get(node);
        this.idToNodeMap.delete(oldId);
        // Set new mappings
        this.idToNodeMap.set(id, node);
        this.nodeToIdMap.set(node, id);
    }

    /**
     * @param { NodeId } id
     * @returns { Node | undefined }
     */
    getNodeById(id) {
        return this.idToNodeMap.get(id);
    }

    /**
     * @param {Node} node
     * @returns {NodeId}
     */
    getNodeId(node) {
        return this.nodeToIdMap.get(node);
    }

    /**
     * @param { Tree } tree
     * @returns { SerializedNode | null }
     */
    serializeTree(tree) {
        const node = tree.node;
        const nodeId = this.getNodeId(node);
        if (!nodeId) {
            return null;
        }
        const result = {
            nodeType: node.nodeType,
            nodeId: nodeId,
        };
        if (node.nodeType === Node.TEXT_NODE) {
            result.textValue = node.nodeValue;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            const childTreesToSerialize = this.processThrough(
                "serializable_descendants_processors",
                tree.children,
                node
            );
            result.tagName = node.tagName;
            result.attributes = Object.fromEntries(
                [...node.attributes].map((attr) => [attr.name, attr.value])
            );
            result.children = childTreesToSerialize
                .map((tree) => this.serializeTree(tree))
                .filter(Boolean);
        }
        return result;
    }

    /**
     * Unserialize a node and its children.
     *
     * @param { SerializedNode } node
     * @returns { Node | null }
     */
    unserializeNode(node) {
        /** @type { Map<Node, string> } */
        const newNodesMap = new Map();
        /**
         * Recursive helper.
         *
         * @param { SerializedNode } serializedNode
         * @returns { Node | null }
         */
        const unserialize = (serializedNode) => {
            let node = this.getNodeById(serializedNode.nodeId);
            if (!node) {
                if (serializedNode.nodeType === Node.TEXT_NODE) {
                    node = this.document.createTextNode(serializedNode.textValue);
                } else if (serializedNode.nodeType === Node.ELEMENT_NODE) {
                    node = this.document.createElement(serializedNode.tagName);
                    for (const key in serializedNode.attributes) {
                        node.setAttribute(key, serializedNode.attributes[key]);
                    }
                    node.append(...serializedNode.children.map(unserialize).filter(Boolean));
                } else {
                    console.warn(`Can't unserialize a node of type ${serializedNode.nodeType}.`);
                    return null;
                }
                newNodesMap.set(node, serializedNode.nodeId);
            }
            return node;
        };

        let unserializedNode = unserialize(node);
        if (unserializedNode) {
            let parent = unserializedNode.parentElement;
            const hasParent = !!parent;
            if (!hasParent) {
                parent = unserializedNode.parentElement || this.document.createElement("fake-el");
                parent.appendChild(unserializedNode);
            }
            this.dependencies.sanitize.sanitize(parent);
            unserializedNode = hasParent ? unserializedNode : parent.firstChild;
            if (unserializedNode) {
                // Only assing id to the remaining nodes, otherwise the
                // removed nodes will still be accessible through the
                // nodeMap and could lead to security issues.
                for (const node of [unserializedNode, ...descendants(unserializedNode)]) {
                    if (!this.hasNode(node)) {
                        const id = newNodesMap.get(node);
                        if (id) {
                            this.set(id, node);
                        }
                    }
                }
                return unserializedNode;
            }
        }
        return null;
    }

    /**
     * @returns { NodeId  }
     */
    generateId() {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2, 52)).toString();
    }
}
