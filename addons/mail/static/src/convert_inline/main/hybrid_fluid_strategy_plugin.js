import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { Analysis, ElementLayout, EmailNode } from "../core/render_models";

const { DESKTOP, MOBILE } = DIMENSIONS;
// Prevent the last inline-block element from wrapping to the next line due
// to window zoom px rounding in some cases.
const ZOOM_WIDTH_CORRECTION = 0.1;

export class HybridFluidStrategyPlugin extends Plugin {
    static id = "hybridFluidStrategy";
    static dependencies = [
        "dynamicStyleSheet",
        "measurementSnapshot",
        "math",
        "responsiveBlock",
        "rules",
        "referenceNode",
    ];
    resources = {
        element_layout_analysis_processors: this.analyzeElementLayout.bind(this),
        synthetic_email_node_processors: this.addSyntheticEmailNode.bind(this),
    };

    setup() {
        this.addToStyleSheet(
            ".o-ci-hybrid-fluid-cell, .o-ci-hybrid-fluid-cell-with-offset",
            { "max-width": { value: "100%", priority: "important" } },
            768
        );
    }

    // TODO EGGMAIL NOW:
    // we have a container which is supposed to be a hybrid fluid table
    // with potentially multiple rows, each with potentially multiple
    // cells.
    // however right now, we only have one container and its children
    // we have to create a EmailNode for each row, and a EmailNode
    // for each cell.
    // some of the existing children can be used as is as a cell
    // the current emailNode should be replaced with the list of rows
    // need feature to insert multiple nodes as children of another
    // emailNode
    // features needed here:
    // - replace an item in emailNode.children
    // // currently setParent appends -> this is not enough
    // // -> honestly, need to replace the set by a special set+list structure
    // // done
    // Logic:
    // exact copy paste of buildFragment logic except we create a datastructure of
    // template arguments instead of the templates directly?
    // Real idea here is that I should create a synthetic emailNode
    // I already have my basic emailNode from the first pass which identifies the row
    // and potentially some other emailNode as children of that row that may have any purpose.
    // Objective here is to make sure that every child of the row is classified as a CELL,
    // be it a child itself becomes a CELL, or 1+ children are wrapped in a CELL
    // BTW the row node itself can become multiple row in some circumstances
    addSyntheticEmailNode(emailNode) {
        // TODO EGGMAIL: arbitrary choice to take the last referenceNode to motivate
        const referenceNode = emailNode.lastReferenceNode;
        const parent = emailNode.parent;
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        const rows = [];
        // TODO EGGMAIL: some values for text-align are not supported
        // getStylePropertyValue should probably filter values and only
        // return what is allowed
        // TODO EGGMAIL: style should probably be refined in this fragment
        const styleContext = {
            style: {
                "text-align": this.getStylePropertyValue(referenceNode, "text-align"),
                "font-size": this.getStylePropertyValue(referenceNode, "font-size"),
            },
        };
        for (const band of desktopBlock.bands) {
            const rowAnalysis = new EmailNode({
                // TODO EGGMAIL: currently oversimplified layout, add tracking of positioning values.
                layout: new ElementLayout({ tag: "div" }),
                analysis: new Analysis({
                    facts: { isHybridFluidRow: true },
                }),
            });
            rows.push(rowAnalysis);
            let prevCluster;
            if (band.clusters.length > 0) {
                prevCluster = band.clusters[0];
                const isLast = band.clusters.length === 1;
                if (!this.isZero(desktopBlock.padding.left)) {
                    const offsetWidth = desktopBlock.padding.left;
                    rowAnalysis.appendChild(
                        this.buildCellWithOffset(
                            emailNode,
                            offsetWidth,
                            prevCluster,
                            styleContext,
                            isLast
                        )
                    );
                } else {
                    rowAnalysis.appendChild(
                        this.buildCell(emailNode, prevCluster, styleContext, isLast)
                    );
                }
            }
            for (let i = 1; i < band.clusters.length; i++) {
                const cluster = band.clusters[i];
                const gap = this.gapX(prevCluster.rect, cluster.rect);
                const isLast = i === band.clusters.length - 1;
                if (gap > 0) {
                    rowAnalysis.appendChild(
                        this.buildCellWithOffset(emailNode, gap, cluster, styleContext, isLast)
                    );
                } else {
                    rowAnalysis.appendChild(
                        this.buildCell(emailNode, prevCluster, styleContext, isLast)
                    );
                }
                prevCluster = cluster;
            }
            if (!this.isZero(desktopBlock.padding.right)) {
                rowAnalysis.appendChild(this.buildEmptyCell(desktopBlock.padding.right));
            }
        }
        parent.spliceChildren(parent.children.indexOf(emailNode), 1, ...rows);
    }

    analyzeElementLayout({ layout, analysis }, { referenceNode }) {
        if (analysis.isFrozen || !this.detectHybridFluidLayout(referenceNode)) {
            return;
        }
        Object.assign(analysis.parsingFacts, {
            canMerge: false,
            addSyntheticEmailNode: true,
        });
        analysis.facts.isHybridFluidRow = true;
        layout.pluginIds.add(HybridFluidStrategyPlugin.id);
    }

    /**
     * TODO EGGMAIL: can I get an hybrid fluid row with only inline children? to investigate
     */
    detectHybridFluidLayout(referenceNode) {
        // detect hybrid fluid "rows"
        // -> detect a band with multiple clusters inside a block
        // -> look in mobile mode, the amount of bands should be different
        // -> should not be captured by table, since the table strictly verifies
        // that the amount of bands is the same
        let isHybridFluidCandidate;
        const mobileBlock = this.getLayoutBlock(referenceNode, MOBILE);
        const desktopBlock = this.getLayoutBlock(referenceNode, DESKTOP);
        if (!desktopBlock || !mobileBlock) {
            return;
        }
        if (desktopBlock.bands.length !== mobileBlock.bands.length) {
            isHybridFluidCandidate = true;
        } else {
            for (const [dBand, mBand] of zip(desktopBlock.bands, mobileBlock.bands)) {
                if (dBand.clusters.length !== mBand.clusters.length) {
                    isHybridFluidCandidate = true;
                    break;
                }
            }
        }
        return isHybridFluidCandidate;
    }

    /**
     * TODO EGGMAIL: test how this works/find a more optimized solution?
     * Evaluate which children in emailNode are related to a given cluster
     * of nodes
     */
    getClusterAnalysis(emailNode, cluster) {
        const range = this.getNodeClusterRange(cluster.nodes.at(0), cluster.nodes.at(-1));
        const clusterAnalysis = [];
        for (const childAnalysis of emailNode.children) {
            if (
                childAnalysis.referenceNodes.length &&
                range.comparePoint(childAnalysis.firstReferenceNode, 0) === 0
            ) {
                clusterAnalysis.push(childAnalysis);
            }
        }
        return clusterAnalysis;
    }

    buildCell(emailNode, cluster, styleContext, isLast = false) {
        const clusterAnalysis = this.getClusterAnalysis(emailNode, cluster);
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        const cellAnalysis = new EmailNode({
            // TODO EGGMAIL: currently oversimplified layout, to elaborate?
            layout: new ElementLayout({ tag: "div" }),
            analysis: new Analysis({
                facts: {
                    isHybridFluidCell: true,
                    // TODO EGGMAIL: move refs in layout?
                    refs: {
                        root: { style: { "max-width": `${clusterWidth}px` } },
                        styleContext,
                    },
                },
            }),
        });
        for (const child of clusterAnalysis) {
            cellAnalysis.appendChild(child);
        }
        return cellAnalysis;
    }

    buildEmptyCell(width) {
        return new EmailNode({
            layout: new ElementLayout({ tag: "div" }),
            analysis: new Analysis({
                facts: {
                    isHybridFluidCell: true,
                    isEmpty: true,
                    refs: {
                        root: { style: { "max-width": `${width}px` } },
                    },
                },
            }),
        });
    }

    buildCellWithOffset(emailNode, offsetWidth, cluster, styleContext, isLast = false) {
        // TODO EGGMAIL: should a cell + offset be considered differently from a normal cell?
        // It behaves like a row inside a row.
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        const offsetAnalysis = this.buildEmptyCell(offsetWidth);
        const cellAnalysis = this.buildCell(emailNode, cluster, styleContext);
        const cellWithOffsetAnalysis = new EmailNode({
            layout: new ElementLayout({ tag: "div" }),
            analysis: new Analysis({
                facts: {
                    isHybridFluidCell: true,
                    isCellWithOffset: true,
                },
                refs: {
                    root: { style: { "max-width": `${offsetWidth + clusterWidth}px` } },
                },
            }),
        });
        cellWithOffsetAnalysis.appendChild(offsetAnalysis);
        cellWithOffsetAnalysis.appendChild(cellAnalysis);
        return cellWithOffsetAnalysis;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(HybridFluidStrategyPlugin.id, HybridFluidStrategyPlugin);
