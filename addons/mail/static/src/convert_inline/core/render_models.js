import { xml } from "@odoo/owl";
import { renderToFragment } from "@web/core/utils/render";
import { ObjectMap, SetMap, UniqueArray } from "../data_structures";
import { StyleInfo, StyleInfoMap } from "./style_models";
import { renderAttributes } from "./utils";

export class NodePositionManager extends Array {
    registerNodes(nodes = []) {
        const nodeIds = [];
        for (const node of nodes) {
            nodeIds.push(this.length);
            this.push(node);
        }
        return nodeIds;
    }

    setNodePositions(fragment) {
        for (const nodePosition of fragment.querySelectorAll("node-position[data-id]")) {
            const node = this[nodePosition.dataset.id];
            if (node) {
                nodePosition.before(this[nodePosition.dataset.id]);
            }
            nodePosition.remove();
        }
    }

    renderContext(context = {}) {
        const { nodes } = context;
        return { ...context, nodeIds: this.registerNodes(nodes) };
    }

    get template() {
        return "mail.NodePositionManager";
    }
}

/**
 * @typedef {Object} ElementOptions
 * @property {Object<string, string>} [attributes={}]
 * @property {string|Iterable<string>} [classNames=""]
 * @property {Object<string, string>} [style={}]
 */

function assignAttributes(target, source) {
    if (source.attributes !== undefined) {
        target.attributes ??= {};
        for (const [name, value] of Object.entries(source.attributes)) {
            target.attributes[name] = value;
        }
    }
}

function assignClassNames(target, source) {
    if (source.classNames !== undefined) {
        target.classNames = source.classNames;
    }
}

function assignStyle(target, source) {
    if (source.style !== undefined) {
        target.style = StyleInfo.from(target.style ?? {});
        target.style.merge(StyleInfo.from(source.style));
    }
}

export function assignDefaultElementOptions(options = {}, defaultOptions = {}) {
    const newOptions = {};
    assignAttributes(newOptions, defaultOptions);
    assignAttributes(newOptions, options);
    assignClassNames(newOptions, defaultOptions);
    assignClassNames(newOptions, options);
    assignStyle(newOptions, defaultOptions);
    assignStyle(newOptions, options);
    return newOptions;
}

export class LayoutModel {
    static template = xml``;
    refToAttributes = new ObjectMap();
    refToClassNames = new SetMap();
    refToStyleInfo = new StyleInfoMap();

    /**
     * @param {Object} [options={}]
     * @param {Object<string, ElementOptions>} [options.refs={}] assign ElementOptions to named template refs
     */
    constructor({ refs = {} } = {}) {
        // TODO EGGMAIL: maybe remove the generic class?
        // Generic class for every layoutModel root element
        this.setAttributes({ classNames: "o-ci" });

        for (const [ref, options] of Object.entries(refs)) {
            this.setAttributes(options, ref);
        }
    }

    get template() {
        return this.constructor.template;
    }

    /**
     * @param {ElementOptions} options
     * @param {string} ref named ref (@see renderAttributes calls) in the template
     */
    setAttributes({ attributes = {}, classNames = "", style = {} } = {}, ref = "root") {
        this.refToAttributes.assign(attributes, ref);
        this.refToStyleInfo.assign(style, ref);
        this.refToClassNames.union(classNames, ref);
    }

    renderAttributes(ref = "root") {
        return renderAttributes({
            attributes: this.refToAttributes.get(ref),
            classNames: this.refToClassNames.get(ref),
            styleInfo: this.refToStyleInfo.get(ref),
        });
    }

    renderContext(context = {}) {
        return { ...context, model: this };
    }

    renderToFragment() {
        const nodePositionManager = new NodePositionManager();
        const fragment = renderToFragment(
            this.template,
            this.renderContext({ nodePositionManager })
        );
        nodePositionManager.setNodePositions(fragment);
        return fragment;
    }
}

export class LayoutModelRef extends LayoutModel {
    static template = "mail.LayoutModelRef";

    constructor({ hooks = {} } = {}) {
        super(...arguments);
        this.hooks = hooks;
    }
}

export class LayoutModelRefChildNodes extends LayoutModelRef {
    constructor({ childNodes = [], hooks = {} } = {}) {
        super(...arguments);
        this.childNodes = childNodes;
        if (!hooks.content) {
            this.hooks.content = { isTemplate: true, template: "mail.LayoutModelChildNodes" };
        }
    }
}

export class LayoutModelRefTag extends LayoutModelRefChildNodes {
    constructor({ hooks = {}, tag } = {}) {
        super(...arguments);
        this.tag = tag;
        if (!hooks.content) {
            this.hooks.content = { isTemplate: true, template: "mail.LayoutModelTag" };
        }
    }
}

export class LayoutModelList extends LayoutModelRef {
    constructor({ hooks = {}, modelList = [] } = {}) {
        super(...arguments);
        this.modelList = modelList;
        if (!hooks.content) {
            this.hooks.content = { isTemplate: true, template: "mail.LayoutModelList" };
        }
    }
}

/**
 * TODO EGGMAIL: remove/move/adapt ?
 */

export class LayoutTable extends LayoutModel {
    rows = [];

    addRow(row) {
        this.rows.push(row);
    }
}

export class LayoutRow extends LayoutModel {
    cells = [];

    addCell(cell) {
        this.cells.push(cell);
    }
}

export class LayoutCell extends LayoutModel {
    constructor({ childNodes = [] } = {}) {
        super(...arguments);
        this.childNodes = childNodes;
    }
}

/**
 * TODO EGGMAIL: simplify/flatten model and combine properties with EmailNode?
 */
export class Analysis {
    parsingFacts = {};
    constraintsForAncestors = [];
    constraintsForDescendants = [];
    facts = {};
    isFrozen = false;

    constructor(options = {}) {
        options.parsingFacts ??= {
            canMerge: false,
            canParentMerge: false,
        };
        this.merge(options);
    }

    /**
     * Informative freeze to indicate that further analysis evaluation is
     * most likely unnecessary / could be wrong
     */
    freeze() {
        this.isFrozen = true;
    }

    merge(analysis) {
        Object.assign(this.parsingFacts, analysis.parsingFacts ?? {});
        this.constraintsForAncestors = this.constraintsForAncestors.concat(
            analysis.constraintsForAncestors
        );
        this.constraintsForDescendants = this.constraintsForDescendants.concat(
            analysis.constraintsForDescendants
        );
        Object.assign(this.facts, analysis.facts ?? {});
        return this;
    }
}

export function renderEmailNode(emailNode) {
    return emailNode.layout.renderToFragment({
        children: emailNode.children.map((child) => renderEmailNode(child)),
    });
}

export class EmailNode {
    referenceNodes = new UniqueArray();
    analysis = new Analysis();
    children = new UniqueArray();

    constructor({ layout, referenceNode, parent, analysis = {} } = {}) {
        this.layout = layout;
        if (parent) {
            parent.appendChild(this);
        }
        if (referenceNode) {
            this.pushReferenceNode(referenceNode);
        }
        this.analysis.merge(analysis);
    }

    spliceChildren(start, deleteCount, ...items) {
        const removedChildren = this.children.splice(start, deleteCount, ...items);
        for (const child of removedChildren) {
            if (!this.children.has(child)) {
                child.parent = undefined;
            }
        }
        for (const child of items) {
            if (child.parent && child.parent.children !== this.children) {
                child.parent.removeChild(child);
            }
            child.parent = this;
        }
        return removedChildren;
    }

    pushReferenceNode(referenceNode) {
        return this.referenceNodes.push(referenceNode);
    }

    get firstReferenceNode() {
        return this.referenceNodes.at(0);
    }

    get lastReferenceNode() {
        return this.referenceNodes.at(-1);
    }

    appendChild(emailNode) {
        if (emailNode.parent && emailNode.parent !== this) {
            emailNode.parent.removeChild(emailNode);
        }
        emailNode.parent = this;
        return this.children.push(emailNode);
    }

    removeChild(emailNode) {
        if (this.children.has(emailNode)) {
            emailNode.parent = undefined;
            return this.children.delete(emailNode);
        } else {
            return false;
        }
    }

    get firstChild() {
        return this.children.at(0);
    }

    get lastChild() {
        return this.children.at(-1);
    }
}

class Layout {
    pluginIds = new Set();

    /**
     * Can be overridden to define how 2 identities should be merged together
     */
    merge(originalLayout) {
        return originalLayout;
    }
}

/**
 * TODO EGGMAIL: implement API so that plugins can modify/define characteristics?
 * Objective of layout is to provide an API for a LayoutModel to get the required arguments
 * for that layoutModel.
 * => layout is closely related to a node, either text or element
 */
export class ElementLayout extends Layout {
    tag;
    styleInfo = new StyleInfo();
    attributes = {};
    classNames = new Set();

    constructor(options) {
        options ??= {};
        super(options);
        this.tag = options.tag;
        this.setAttributes(options);
    }

    merge(originalLayout) {
        originalLayout.setAttributes(this);
        originalLayout.tag = this.tag;
        return originalLayout;
    }

    setAttributes({ attributes = {}, classNames = "", style = {} } = {}) {
        Object.assign(this.attributes, attributes);
        if (typeof classNames === "string") {
            classNames = classNames.split(" ").filter(Boolean);
        }
        this.classNames = this.classNames.union(new Set(classNames));
        this.styleInfo.merge(StyleInfo.from(style), this.styleInfo.maxSequence);
    }

    get style() {
        return this.styleInfo;
    }
}

export class TextLayout extends Layout {
    content;

    constructor({ content } = {}) {
        super(...arguments);
        // TODO EGGMAIL: same consideration as ElementLayout: do we really
        // need node details? We could just get it from the actual node later.
        this.content = content;
    }
}
