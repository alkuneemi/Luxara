import { UniqueArray } from "../data_structures";
import { StyleInfo } from "./style_models";

export class NodeInfo {
    isDiscarded = false;

    constructor({ referenceNode }) {
        // node from this.config.reference
        this.referenceNode = referenceNode;
    }
}

export class Analysis {
    parsingConstraints = {};
    ancestorConstraints = {};
    descendantConstraints = {};
    facts = {};
    isFrozen = false;

    constructor(options = {}) {
        options.parsingConstraints ??= {
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
        Object.assign(this.parsingConstraints, analysis.parsingConstraints ?? {});
        Object.assign(this.ancestorConstraints, analysis.ancestorConstraints ?? {});
        Object.assign(this.descendantConstraints, analysis.descendantConstraints ?? {});
        Object.assign(this.facts, analysis.facts ?? {});
        return this;
    }
}

export class NodeAnalysis {
    nodeInfos = new UniqueArray();
    analysis = new Analysis();
    children = new UniqueArray();

    constructor({ identity, nodeInfo, parent, analysis = {} } = {}) {
        this.identity = identity;
        this.setParent(parent);
        this.pushNodeInfo(nodeInfo);
        this.analysis.merge(analysis);
    }

    setParent(parent) {
        if (this.parent === parent) {
            return;
        }
        if (this.parent) {
            this.parent.deleteChild(this);
        }
        this.parent = parent || undefined;
        if (this.parent) {
            this.parent.appendChild(this);
        }
    }

    pushNodeInfo(nodeInfo) {
        return this.nodeInfos.push(nodeInfo);
    }

    get firstNodeInfo() {
        return this.nodeInfos.at(0);
    }

    get lastNodeInfo() {
        return this.nodeInfos.at(-1);
    }

    appendChild(nodeAnalysis) {
        return this.children.push(nodeAnalysis);
    }

    deleteChild(nodeAnalysis) {
        return this.children.delete(nodeAnalysis);
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

    /**
     * TODO EGGMAIL: evaluate if we really need the following here
     * (maybe it's enough to store nodeInfo)
     */
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
