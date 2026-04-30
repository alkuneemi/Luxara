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
        "node",
    ];
    resources = {
        apply_layout_strategy_overrides: this.applyLayoutStrategy.bind(this),
        element_identity_analysis_processors: this.analyzeElementIdentity.bind(this),
        attribute_rules_processors: [
            [this.provideAttributeRules.bind(this), ImageStrategyPlugin.id],
        ],
    };

    // fix images padding
    // padding concern is only there for microsoft outlook => should be solved then
    // that concern is actually there for any node which is not a td
    // either keep padding on image to stay coherent with the current padding logic
    // OR remove padding everywhere and make it a MSO concern?
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

    provideAttributeRules(rules) {
        // height and width attributes are specified through applyLayoutStrategy
        rules.block("height", { when: this.isImg.bind(this) });
        rules.block("width", { when: this.isImg.bind(this) });
    }

    isImg({ referenceNode }) {
        return referenceNode.nodeName === "IMG";
    }

    analyzeElementIdentity({ identity, analysis }, { referenceNode }) {
        if (analysis.isFrozen) {
            return;
        }
        let detectionResult = this.detectImageLink(referenceNode);
        if (detectionResult) {
            analysis.facts.isImageLink = true;
            analysis.facts.imageLinkData = detectionResult;
        } else if ((detectionResult = this.detectImage(referenceNode))) {
            analysis.facts.isImage = true;
            analysis.facts.imageData = detectionResult;
        }
        if (detectionResult) {
            Object.assign(analysis.parsingFacts, {
                canMerge: false,
                canParentMerge: false,
            });
            identity.pluginIds.add(ImageStrategyPlugin.id);
        }
    }

    applyLayoutStrategy(referenceNode) {
        let detectionResult;
        if ((detectionResult = this.detectImageLink(referenceNode))) {
            this.buildImageLinkFragment(detectionResult);
        } else if ((detectionResult = this.detectImage(referenceNode))) {
            this.buildImageFragment(detectionResult);
        }
        if (detectionResult) {
            for (const referenceNode of detectionResult.referenceNodes) {
                referenceNode.defineLayoutStrategy({ pluginId: ImageStrategyPlugin.id });
            }
            return true;
        }
    }

    detectImageLink(referenceNode) {
        if (referenceNode.nodeName === "A") {
            const visibleChildNodes = this.processChildNodes(
                referenceNode,
                (node) => !this.isInvisible(node)
            );
            if (visibleChildNodes.length === 1 && visibleChildNodes[0].nodeName === "IMG") {
                const imageNode = visibleChildNodes[0];
                return {
                    imageNode: imageNode,
                    linkNode: referenceNode,
                    shouldBeBlock: this.shouldBeBlock(referenceNode),
                };
            }
        }
    }

    detectImage(referenceNode) {
        if (this.isImg(referenceNode)) {
            return {
                imageNode: referenceNode,
                shouldBeBlock: this.shouldBeBlock(referenceNode),
            };
        }
    }

    shouldBeBlock(referenceNode) {
        if (this.isBlock(referenceNode)) {
            return true;
        }
        const isVisibleBlock = (node) => this.isBlock(node) && !this.isInvisible(node);
        const prevSibling = referenceNode.previousSibling;
        const nextSibling = referenceNode.nextSibling;
        const parent = referenceNode.parentElement;
        return (
            this.isBlock(parent) &&
            (!prevSibling || isVisibleBlock(prevSibling)) &&
            (!nextSibling || isVisibleBlock(nextSibling))
        );
    }

    buildImageLinkFragment({ imageNode, linkNode, shouldBeBlock }) {
        const styleInfo = new StyleInfo();
        styleInfo.setProperty("text-decoration", "none");
        if (shouldBeBlock) {
            styleInfo.setProperty("display", "block");
        }
        styleInfo.applyOnElement(linkNode.fragment.firstElementChild);
        this.buildImageFragment({ imageNode, shouldBeBlock });
    }

    buildImageFragment({ imageNode, shouldBeBlock }) {
        const img = imageNode.fragment.firstElementChild;
        img.replaceChildren();
        const style = Object.assign(
            { "border-width": { value: "0", priority: "important" } },
            shouldBeBlock ? { display: "block" } : {}
        );
        const dimensions = this.extractImageDimensions(imageNode);
        Object.assign(style, dimensions.style);
        StyleInfo.from(style).applyOnElement(img);
        for (const [name, value] of Object.entries(dimensions.attributes)) {
            img.setAttribute(name, value);
        }
    }

    extractImageDimensions(referenceNode) {
        const styleInfo = this.getStyleInfo(referenceNode);
        const attributes = {};
        const style = {};
        const width = parseCssValue(styleInfo.getPropertyValue("width"));
        const height = parseCssValue(styleInfo.getPropertyValue("height"));
        const maxWidth = parseCssValue(styleInfo.getPropertyValue("max-width"));
        width.rendered = this.getStyleWidth(referenceNode);
        width.natural = referenceNode.naturalWidth;
        height.natural = referenceNode.naturalHeight;
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
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(ImageStrategyPlugin.id, ImageStrategyPlugin);
