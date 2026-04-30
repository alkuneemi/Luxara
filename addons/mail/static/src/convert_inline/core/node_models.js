import { UniqueArray } from "../data_structures";
import { StyleInfo } from "./style_models";

/**
 * TODO EGGMAIL: simplify/flatten model and combine properties with NodeAnalysis?
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

export class NodeAnalysis {
    referenceNodes = new UniqueArray();
    analysis = new Analysis();
    children = new UniqueArray();

    constructor({ identity, referenceNode, parent, analysis = {} } = {}) {
        this.identity = identity;
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

    appendChild(nodeAnalysis) {
        if (nodeAnalysis.parent && nodeAnalysis.parent !== this) {
            nodeAnalysis.parent.removeChild(nodeAnalysis);
        }
        nodeAnalysis.parent = this;
        return this.children.push(nodeAnalysis);
    }

    removeChild(nodeAnalysis) {
        if (this.children.has(nodeAnalysis)) {
            nodeAnalysis.parent = undefined;
            return this.children.delete(nodeAnalysis);
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

class Identity {
    pluginIds = new Set();

    /**
     * Can be overridden to define how 2 identities should be merged together
     */
    merge(originalIdentity) {
        return originalIdentity;
    }
}

/**
 * TODO EGGMAIL: implement API so that plugins can modify/define characteristics?
 * Objective of identity is to provide an API for a LayoutModel to get the required arguments
 * for that layoutModel.
 * => identity is closely related to a node, either text or element
 */
export class ElementIdentity extends Identity {
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

    merge(originalIdentity) {
        originalIdentity.setAttributes(this);
        originalIdentity.tag = this.tag;
        return originalIdentity;
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

export class TextIdentity extends Identity {
    content;

    constructor({ content } = {}) {
        super(...arguments);
        // TODO EGGMAIL: same consideration as ElementIdentity: do we really
        // need node details? We could just get it from the actual node later.
        this.content = content;
    }
}
