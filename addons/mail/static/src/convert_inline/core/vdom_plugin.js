import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { NodeInfo } from "./vdom_models";

export class VDomPlugin extends Plugin {
    static id = "vDom";
    static shared = [
        "createReferenceTreeWalker",
        "createTemplateNode",
        "getNodeInfo",
        "processChildNodes",
        "renderEmailHtml",
    ];
    resources = {
        on_render_email_template_handlers: this.renderEmailHtml.bind(this),
    };

    setup() {
        this.referenceToInfo = new WeakMap();
        this.vNodeToInfo = new WeakMap();
        this.renderIdToInfo = new Map();
    }

    processChildNodes(node, callback = () => {}) {
        const nodes = [];
        let child = node.firstChild;
        while (child) {
            const currentChild = child;
            child = child.nextSibling;
            if (![Node.ELEMENT_NODE, Node.TEXT_NODE].includes(currentChild.nodeType)) {
                continue;
            }
            if (callback(currentChild) !== false) {
                nodes.push(currentChild);
            }
        }
        return nodes;
    }

    lazyNodeInfoProxyHandler(referenceNode) {
        return {
            get: (target, key, receiver) => {
                if (key === "fragment" && !target.fragment) {
                    // Ensure that during the final rendering, if no plugin
                    // ever modified the fragment associated with a reference
                    // node, it contains its clone and references to its
                    // childNodes.
                    target.fragment = this.config.referenceDocument.createDocumentFragment();
                    const templateNode = this.createTemplateNode(target);
                    const childNodeList = this.processChildNodes(referenceNode);
                    for (const child of childNodeList) {
                        const nodeInfo = this.getNodeInfo(child);
                        if (!nodeInfo.vNode.parentNode && !nodeInfo.isDiscarded) {
                            templateNode.appendChild(nodeInfo.vNode);
                        }
                    }
                    target.fragment.appendChild(templateNode);
                }
                return Reflect.get(target, key, receiver);
            },
        };
    }

    createTemplateNode(nodeInfo) {
        const { referenceNode } = nodeInfo;
        const templateNode =
            referenceNode === this.config.reference
                ? this.config.referenceDocument.createDocumentFragment()
                : referenceNode.cloneNode();
        return this.processThrough("template_node_processors", templateNode, nodeInfo);
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
                const vNode = this.config.referenceDocument.createComment("");
                nodeInfo = new Proxy(
                    new NodeInfo({
                        referenceNode: node,
                        vNode,
                    }),
                    this.lazyNodeInfoProxyHandler(node)
                );
                this.vNodeToInfo.set(vNode, nodeInfo);
                // TODO EGGMAIL: maybe agglomerate multiple nodes to a single
                // "nodeInfo", maybe reword this a `nodePattern`
                this.referenceToInfo.set(node, nodeInfo);
            }
        } else if (this.vNodeToInfo.has(node)) {
            nodeInfo = this.vNodeToInfo.get(node);
        } else if (this.lastRenderTemplate?.contains(node)) {
            if (node.nodeType === Node.ELEMENT_NODE) {
                const renderElement = node.closest("[data-render-id]");
                nodeInfo = this.renderIdToInfo.get(renderElement.dataset.renderId);
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

    cloneReferenceFragment(nodeInfo, options = {}) {
        const { withRenderId } = options;
        const fragment = nodeInfo.fragment;
        const renderFragment = fragment.cloneNode(true);
        const vWalker = this.config.referenceDocument.createTreeWalker(
            fragment,
            NodeFilter.SHOW_COMMENT
        );
        const renderWalker = this.config.referenceDocument.createTreeWalker(
            renderFragment,
            NodeFilter.SHOW_COMMENT
        );
        let vNode, renderNode;
        while ((vNode = vWalker.nextNode()) && (renderNode = renderWalker.nextNode())) {
            if (this.vNodeToInfo.has(vNode)) {
                this.vNodeToRenderNode.set(vNode, renderNode);
                if (withRenderId && renderNode.nodeType === Node.ELEMENT_NODE) {
                    renderNode.dataset.renderId = nodeInfo.renderId;
                    this.renderIdToInfo.set(nodeInfo.renderId, nodeInfo);
                }
            }
        }
        return renderFragment;
    }

    createReferenceTreeWalker(filter = () => NodeFilter.FILTER_ACCEPT) {
        return this.config.referenceDocument.createTreeWalker(
            this.config.reference,
            NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
            filter
        );
    }

    renderReferenceFragment(nodeInfo, options = {}) {
        const renderNode = this.vNodeToRenderNode.get(nodeInfo.vNode);
        if (!renderNode) {
            // TODO EGGMAIL: error management, the associated vNode
            // has no position in the current rendering.
            return;
        }
        if (nodeInfo.isDiscarded) {
            renderNode.remove();
            return;
        }
        const renderFragment = this.cloneReferenceFragment(nodeInfo, options);
        renderNode.replaceWith(renderFragment);
        for (const descendant of this.processChildNodes(nodeInfo.referenceNode)) {
            const descendantInfo = this.getNodeInfo(descendant);
            this.renderReferenceFragment(descendantInfo, options);
        }
    }

    ensureTemplateContent(template) {
        if (!template.content.firstChild) {
            const paragraph = this.config.referenceDocument.createElement("P");
            const br = this.config.referenceDocument.createElement("BR");
            paragraph.append(br);
            template.content.appendChild(paragraph);
        }
    }

    /**
     * // TODO EGGMAIL: docstring
     * @param {*} template
     * @param {*} [options]
     * @param {*} [options.withRenderId]
     */
    renderEmailHtml(template, options = {}) {
        // TODO EGGMAIL: give the `reference` as an argument, to be able to
        // start from any point in the rendering tree (render partial tree).
        this.lastRenderTemplate = template;
        this.renderIdToInfo = new Map();
        this.vNodeToRenderNode = new WeakMap();
        const referenceInfo = this.getNodeInfo(this.config.reference);
        const renderNode = referenceInfo.vNode.cloneNode();
        this.vNodeToRenderNode.set(referenceInfo.vNode, renderNode);
        template.content.appendChild(renderNode);
        this.renderReferenceFragment(referenceInfo, options);
        this.vNodeToRenderNode = undefined;
        this.ensureTemplateContent(template);
    }
}

registry.category("mail-html-conversion-core-plugins").add(VDomPlugin.id, VDomPlugin);
