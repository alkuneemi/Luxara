import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { StyleInfo } from "../core/style_models";
import { parseCssValue } from "../css_parsers";

export class ImageStrategyPlugin extends Plugin {
    static id = "imageStrategy";
    static dependencies = [
        "filterContent",
        "measurementSnapshot",
        "responsiveBlock",
        "rules",
        "vDom",
    ];
    resources = {
        apply_layout_strategy_overrides: this.applyLayoutStrategy.bind(this),
        style_rules_processors: [[this.provideStyleRules.bind(this), ImageStrategyPlugin.id]],
    };

    // fix images padding
    // background images => vml strategy?
    // attachment thumbnails
    // media list img without height?
    // object-fit: cover?
    // image with 100% height in cell
    // remove height attribute in card images?
    // card-img-top height?
    // mx-auto in table cells?
    // img with font-family simple quote/double quote issue?
    // font icons to images

    applyLayoutStrategy(nodeInfo) {
        let analysis;
        if ((analysis = this.detectLinkImage(nodeInfo))) {
            this.buildLinkImageFragment(analysis);
        } else if ((analysis = this.detectImage(nodeInfo))) {
            this.buildImageFragment(analysis);
        }
        if (analysis) {
            for (const nodeInfo of analysis.nodeInfos) {
                nodeInfo.defineLayoutStrategy({ pluginId: ImageStrategyPlugin.id });
            }
            return true;
        }
    }

    detectLinkImage(nodeInfo) {
        if (nodeInfo.referenceNode.nodeName === "A") {
            const visibleChildNodes = this.processChildNodes(
                nodeInfo.referenceNode,
                (node) => !this.isInvisible(this.getNodeInfo(node))
            );
            if (visibleChildNodes.length === 1 && visibleChildNodes[0].nodeName === "IMG") {
                const imageNodeInfo = this.getNodeInfo(visibleChildNodes[0]);
                return {
                    imageInfo: imageNodeInfo,
                    linkInfo: nodeInfo,
                    nodeInfos: [nodeInfo, imageNodeInfo],
                };
            }
        }
    }

    detectImage(nodeInfo) {
        if (nodeInfo.referenceNode.nodeName === "IMG") {
            return {
                nodeInfo,
                nodeInfos: [nodeInfo],
            };
        }
    }

    shouldBeBlock(nodeInfo) {
        if (this.isBlock(nodeInfo.referenceNode)) {
            return true;
        }
        const isVisibleBlock = (node) =>
            this.isBlock(node) && !this.isInvisible(this.getNodeInfo(node));
        const prevSibling = nodeInfo.referenceNode.previousSibling;
        const nextSibling = nodeInfo.referenceNode.nextSibling;
        const parent = nodeInfo.referenceNode.parentElement;
        return (
            this.isBlock(parent) &&
            (!prevSibling || isVisibleBlock(prevSibling)) &&
            (!nextSibling || isVisibleBlock(nextSibling))
        );
    }

    buildLinkImageFragment({ imageInfo, linkInfo }) {
        const shouldBeBlock = this.shouldBeBlock(linkInfo);
        const styleInfo = new StyleInfo();
        styleInfo.setProperty("text-decoration", "none");
        if (shouldBeBlock) {
            styleInfo.setProperty("display", "block");
        }
        styleInfo.applyOnElement(linkInfo.fragment.firstElementChild);
        this.buildImageFragment({ nodeInfo: imageInfo, shouldBeBlock });
    }

    buildImageFragment({ nodeInfo, shouldBeBlock }) {
        shouldBeBlock ??= this.shouldBeBlock(nodeInfo);
        const img = nodeInfo.fragment.firstElementChild;
        img.replaceChildren();
        const style = Object.assign(
            { "border-width": { value: "0", priority: "important" } },
            shouldBeBlock ? { display: "block" } : {}
        );
        img.style.removeProperty("height");
        img.style.removeProperty("width");
        img.style.removeProperty("max-width");
        img.removeAttribute("width");
        img.removeAttribute("height");
        const dimensions = this.extractImageDimensions(nodeInfo);
        Object.assign(style, dimensions.style);
        StyleInfo.from(style).applyOnElement(img);
        for (const [name, value] of Object.entries(dimensions.attributes)) {
            img.setAttribute(name, value);
        }
    }

    extractImageDimensions(nodeInfo) {
        const styleInfo = this.getStyleInfo(nodeInfo);
        const attributes = {};
        const style = {};
        const width = parseCssValue(styleInfo.getPropertyValue("width"));
        const height = parseCssValue(styleInfo.getPropertyValue("height"));
        const maxWidth = parseCssValue(styleInfo.getPropertyValue("max-width"));
        width.rendered = this.getStyleWidth(nodeInfo.referenceNode);
        width.natural = nodeInfo.referenceNode.naturalWidth;
        height.natural = nodeInfo.referenceNode.naturalHeight;
        if (height.unit === "px") {
            if (width.unit !== "px") {
                if (width.natural > 0 && height.natural > 0) {
                    width.number = (height.number * width.natural) / height.natural;
                } else {
                    width.number = width.rendered || 0;
                }
                width.unit = "px";
            }
            attributes.width = `${Math.round(width.number)}`;
            attributes.height = `${Math.round(height.number)}`;
            Object.assign(style, { width: `${width.number}px`, height: `${height.number}px` });
        } else if (width.unit === "px") {
            attributes.width = `${Math.round(width.number)}`;
            Object.assign(style, { width: `${width.number}px`, height: "auto" });
        } else {
            style.height = "auto";
            if (width.unit === "%") {
                style.width = `${width.number}%`;
            } else {
                style.width = `100%`;
            }
            if (maxWidth.unit === "px") {
                attributes.width = `${Math.round(maxWidth.number)}`;
                style["max-width"] = `${maxWidth.number}px`;
            } else {
                attributes.width = `${Math.round(width.rendered)}`;
            }
        }
        return { attributes, style };
    }

    provideStyleRules(rules) {
        rules.allow("height", {
            when: ({ nodeInfo }) => nodeInfo.referenceNode.nodeName === "IMG",
        });
        rules.allow("width", {
            when: ({ nodeInfo }) => nodeInfo.referenceNode.nodeName === "IMG",
        });
        rules.allow("max-width", {
            when: ({ nodeInfo }) => nodeInfo.referenceNode.nodeName === "IMG",
        });
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ImageStrategyPlugin.id, ImageStrategyPlugin);
