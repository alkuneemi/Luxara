import { xml } from "@odoo/owl";
import { renderToFragment } from "@web/core/utils/render";
import { ObjectMap, SetMap } from "../maps";
import { StyleInfo, StyleInfoMap } from "./style_models";

export class NodePositionManager extends Array {
    registerNodes(nodes) {
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

    renderContext(nodes) {
        return {
            nodeIds: this.registerNodes(nodes),
        };
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
        return Object.assign(
            {},
            this.refToAttributes.get(ref),
            { class: [...this.refToClassNames.get(ref).values()].join(" ") || undefined },
            { style: this.refToStyleInfo.get(ref).toString() || undefined }
        );
    }

    renderContext(nodePositionManager) {
        return { model: this, nodePositionManager };
    }

    renderToFragment() {
        const nodePositionManager = new NodePositionManager();
        const fragment = renderToFragment(this.template, this.renderContext(nodePositionManager));
        nodePositionManager.setNodePositions(fragment);
        return fragment;
    }
}

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
