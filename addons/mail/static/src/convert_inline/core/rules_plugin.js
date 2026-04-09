import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { StyleInfo } from "./style_models";
import { Rules } from "./rules_models";

export class RulesPlugin extends Plugin {
    static id = "rules";
    static dependencies = ["measurementSnapshot", "style"];
    static shared = [
        "applyAttributeRules",
        "applyStyleRules",
        "cloneReferenceNode",
        "filterAttributes",
        "filterStyleInfo",
        "getAttributes",
        "getStyleInfo",
    ];
    resources = {
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
        on_will_load_reference_content_handlers: this.specifyRules.bind(this),
    };

    setup() {
        this.nodeInfoToStyleInfos = new WeakMap();
    }

    specifyRules() {
        this.attributeRules = this.processRules(
            "attribute_rules_processors",
            new Rules({ defaultAllowed: true })
        );
        this.styleRules = this.processRules("style_rules_processors", new Rules());
    }

    cloneReferenceNode(nodeInfo, layoutDimensions = this.layoutDimensions) {
        const { referenceNode } = nodeInfo;
        let clone;
        if (referenceNode.nodeType === Node.ELEMENT_NODE) {
            clone = this.config.referenceDocument.createElement(referenceNode.tagName);
            this.applyAttributeRules(clone, this.getAttributes(nodeInfo));
            this.applyStyleRules(clone, this.getStyleInfo(nodeInfo, layoutDimensions));
        } else {
            clone = referenceNode.cloneNode();
        }
        return clone;
    }

    getStyleInfoToFiltered(nodeInfo) {
        if (!this.nodeInfoToStyleInfos.has(nodeInfo)) {
            this.nodeInfoToStyleInfos.set(nodeInfo, new WeakMap());
        }
        return this.nodeInfoToStyleInfos.get(nodeInfo);
    }

    applyAttributeRules(targetElement, attributes) {
        if (!targetElement || targetElement.nodeType !== Node.ELEMENT_NODE) {
            return targetElement;
        }
        for (const attributeName of targetElement.getAttributeNames()) {
            targetElement.removeAttribute(attributeName);
        }
        for (const [attributeName, attributeValue] of Object.entries(attributes)) {
            targetElement.setAttribute(attributeName, attributeValue);
        }
        return targetElement;
    }

    filterAttributes(attributes, nodeInfo, rules = this.attributeRules) {
        let attributesMap = attributes;
        if (attributes instanceof Array) {
            attributesMap = new Map(attributes);
        } else if (!(attributes instanceof Map)) {
            attributesMap = new Map(Object.entries(attributes));
        }
        if (!rules) {
            return Object.fromEntries(attributesMap);
        }
        const filteredAttributes = {};
        rules.processData(attributesMap, {
            getRuleArgs: (attributeName, attributeValue) => [
                {
                    attributeName,
                    attributeValue,
                    nodeInfo,
                },
            ],
            onPass: (attributeName, attributeValue, fixedArgs = {}) => {
                filteredAttributes[attributeName] = fixedArgs.attributeValue ?? attributeValue;
            },
            onFail: (attributeName) => {
                delete filteredAttributes[attributeName];
            },
            onMiss: (attributeName) => {
                console.warn(
                    `Attribute ${attributeName} is missing or was marked as blocked on the given attributes, in relation to nodeInfo`,
                    attributes,
                    nodeInfo
                );
            },
        });
        return filteredAttributes;
    }

    getAttributes(nodeInfo) {
        return this.filterAttributes(
            nodeInfo.referenceNode
                .getAttributeNames()
                .map((name) => [name, nodeInfo.referenceNode.getAttribute(name)]),
            nodeInfo
        );
    }

    applyStyleRules(targetElement, styleInfo) {
        if (!targetElement || targetElement.nodeType !== Node.ELEMENT_NODE) {
            return targetElement;
        }
        targetElement.removeAttribute("style");
        styleInfo.applyOnElement(targetElement);
        return targetElement;
    }

    /**
     * Return a new styleInfo instance filtered with rules
     */
    filterStyleInfo(styleInfo, nodeInfo, rules = this.styleRules) {
        const filteredStyleInfo = new StyleInfo();
        if (!rules) {
            return filteredStyleInfo.merge(styleInfo);
        }
        if (rules === this.styleRules) {
            const styleInfoToFiltered = this.getStyleInfoToFiltered(nodeInfo);
            if (styleInfoToFiltered.has(styleInfo)) {
                return filteredStyleInfo.merge(styleInfoToFiltered.get(styleInfo));
            }
        }
        rules.processData(styleInfo, {
            getRuleArgs: (propertyName, propertyInfo) => [
                {
                    propertyName,
                    propertyValue: propertyInfo.value,
                    propertyPriority: propertyInfo.priority,
                    nodeInfo,
                },
            ],
            onPass: (propertyName, propertyInfo, fixedArgs = {}) => {
                filteredStyleInfo.setProperty(
                    propertyName,
                    fixedArgs.propertyValue ?? propertyInfo.value,
                    fixedArgs.propertyPriority ?? propertyInfo.priority,
                    propertyInfo.sequence
                );
            },
            onMiss: (propertyName) => {
                // TODO EGGMAIL NOW: special values like unset, inherit, ... must
                // be handled (either computed style or search parents), need to
                // check units and other values too
                // TODO EGGMAIL: search parents before applying computed style?
                filteredStyleInfo.setProperty(
                    propertyName,
                    this.getStylePropertyValue(nodeInfo.referenceNode)
                );
            },
        });
        if (rules === this.styleRules) {
            const styleInfoToFiltered = this.getStyleInfoToFiltered(nodeInfo);
            styleInfoToFiltered.set(styleInfo, new StyleInfo().merge(filteredStyleInfo));
        }
        return filteredStyleInfo;
    }

    getStyleInfo(nodeInfo, layoutDimensions = this.layoutDimensions) {
        return this.filterStyleInfo(
            this.getRawStyleInfo(nodeInfo.referenceNode, layoutDimensions),
            nodeInfo
        );
    }

    onLayoutDimensionsUpdated(layoutDimensions) {
        this.layoutDimensions = layoutDimensions;
    }
}

registry.category("mail-html-conversion-core-plugins").add(RulesPlugin.id, RulesPlugin);
