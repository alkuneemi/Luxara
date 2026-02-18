import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { StyleInfo } from "./style_models";
import { Rules } from "./rules_models";

export class RulesPlugin extends Plugin {
    static id = "rules";
    static dependencies = ["measurementSnapshot", "style"];
    static shared = ["applyAttributeRules", "applyStyleRules", "filterStyleInfo", "getStyleInfo"];
    resources = {
        on_layout_dimensions_updated_handlers: this.onLayoutDimensionsUpdated.bind(this),
        on_will_load_reference_content_handlers: this.specifyRules.bind(this),
        template_node_processors: this.applyAttributeRules.bind(this),
    };

    setup() {
        this.nodeInfoToStyleInfos = new WeakMap();
    }

    getStyleInfoToFiltered(nodeInfo) {
        if (!this.nodeInfoToStyleInfos.has(nodeInfo)) {
            this.nodeInfoToStyleInfos.set(nodeInfo, new WeakMap());
        }
        return this.nodeInfoToStyleInfos.get(nodeInfo);
    }

    specifyRules() {
        this.attributeRules = this.processRules(
            "attribute_rules_processors",
            new Rules({ defaultAllowed: true })
        );
        this.styleRules = this.processRules("style_rules_processors", new Rules());
    }

    applyAttributeRules(targetElement, nodeInfo, rules = this.attributeRules) {
        if (!rules || !targetElement || targetElement.nodeType !== Node.ELEMENT_NODE) {
            return targetElement;
        }
        const attributes = new Map(
            targetElement
                .getAttributeNames()
                .map((name) => [name, targetElement.getAttribute(name)])
        );
        rules.processData(attributes, {
            getRuleArgs: (attributeName, attributeValue) => [
                {
                    attributeName,
                    attributeValue,
                    nodeInfo,
                    templateNode: targetElement,
                },
            ],
            onPass: (attributeName, _, fixedAttributeValue) => {
                if (fixedAttributeValue !== undefined) {
                    targetElement.setAttribute(attributeName, fixedAttributeValue);
                }
            },
            onFail: (attributeName) => {
                targetElement.removeAttribute(attributeName);
            },
            onMiss: (attributeName) => {
                console.warn(
                    `Attribute ${attributeName} is missing or was marked as blocked on the target element`,
                    targetElement
                );
            },
        });
        return targetElement;
    }

    applyStyleRules(targetElement, nodeInfo, rules = this.styleRules) {
        if (!rules || !targetElement || targetElement.nodeType !== Node.ELEMENT_NODE) {
            return targetElement;
        }
        const styleInfo = this.getStyleInfo(nodeInfo);
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
