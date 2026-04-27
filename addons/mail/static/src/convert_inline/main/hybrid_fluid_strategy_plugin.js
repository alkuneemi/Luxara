import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import { DIMENSIONS } from "../hooks";
import { Analysis, ElementIdentity, NodeAnalysis } from "../core/node_models";

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
        "nodeInfo",
    ];
    resources = {
        element_identity_analysis_processors: this.analyzeElementIdentity.bind(this),
        synthetic_node_analysis_processors: this.addSyntheticNodeAnalysis.bind(this),
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
    // we have to create a NodeAnalysis for each row, and a NodeAnalysis
    // for each cell.
    // some of the existing children can be used as is as a cell
    // the current nodeAnalysis should be replaced with the list of rows
    // need feature to insert multiple nodes as children of another
    // nodeAnalysis
    // features needed here:
    // - replace an item in nodeAnalysis.children
    // // currently setParent appends -> this is not enough
    // // -> honestly, need to replace the set by a special set+list structure
    // // done
    // Logic:
    // exact copy paste of buildFragment logic except we create a datastructure of
    // template arguments instead of the templates directly?
    // Real idea here is that I should create a synthetic nodeAnalysis
    // I already have my basic nodeAnalysis from the first pass which identifies the row
    // and potentially some other nodeAnalysis as children of that row that may have any purpose.
    // Objective here is to make sure that every child of the row is classified as a CELL,
    // be it a child itself becomes a CELL, or 1+ children are wrapped in a CELL
    // BTW the row node itself can become multiple row in some circumstances
    addSyntheticNodeAnalysis(nodeAnalysis) {
        // TODO EGGMAIL: arbitrary choice to take the last nodeInfo to motivate
        const nodeInfo = nodeAnalysis.lastNodeInfo;
        const parent = nodeAnalysis.parent;
        const desktopBlock = this.getLayoutBlock(nodeInfo.referenceNode, DESKTOP);
        const rows = [];
        // TODO EGGMAIL: some values for text-align are not supported
        // getStylePropertyValue should probably filter values and only
        // return what is allowed
        // TODO EGGMAIL: style should probably be refined in this fragment
        const styleContext = {
            style: {
                "text-align": this.getStylePropertyValue(nodeInfo.referenceNode, "text-align"),
                "font-size": this.getStylePropertyValue(nodeInfo.referenceNode, "font-size"),
            },
        };
        for (const band of desktopBlock.bands) {
            const rowAnalysis = new NodeAnalysis({
                // TODO EGGMAIL: currently oversimplified identity, add tracking of positioning values.
                identity: new ElementIdentity({ tag: "div" }),
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
                            nodeAnalysis,
                            offsetWidth,
                            prevCluster,
                            styleContext,
                            isLast
                        )
                    );
                } else {
                    rowAnalysis.appendChild(
                        this.buildCell(nodeAnalysis, prevCluster, styleContext, isLast)
                    );
                }
            }
            for (let i = 1; i < band.clusters.length; i++) {
                const cluster = band.clusters[i];
                const gap = this.gapX(prevCluster.rect, cluster.rect);
                const isLast = i === band.clusters.length - 1;
                if (gap > 0) {
                    rowAnalysis.appendChild(
                        this.buildCellWithOffset(nodeAnalysis, gap, cluster, styleContext, isLast)
                    );
                } else {
                    rowAnalysis.appendChild(
                        this.buildCell(nodeAnalysis, prevCluster, styleContext, isLast)
                    );
                }
                prevCluster = cluster;
            }
            if (!this.isZero(desktopBlock.padding.right)) {
                rowAnalysis.appendChild(this.buildEmptyCell(desktopBlock.padding.right));
            }
        }
        parent.spliceChildren(parent.children.indexOf(nodeAnalysis), 1, ...rows);
    }

    analyzeElementIdentity({ identity, analysis }, { nodeInfo }) {
        if (analysis.isFrozen || !this.detectHybridFluidLayout(nodeInfo)) {
            return;
        }
        Object.assign(analysis.parsingConstraints, {
            canMerge: false,
            addSyntheticNodeAnalysis: true,
        });
        analysis.facts.isHybridFluidRow = true;
        identity.pluginIds.add(HybridFluidStrategyPlugin.id);
    }

    /**
     * TODO EGGMAIL: can I get an hybrid fluid row with only inline children? to investigate
     */
    detectHybridFluidLayout(nodeInfo) {
        // detect hybrid fluid "rows"
        // -> detect a band with multiple clusters inside a block
        // -> look in mobile mode, the amount of bands should be different
        // -> should not be captured by table, since the table strictly verifies
        // that the amount of bands is the same
        let isHybridFluidCandidate;
        const mobileBlock = this.getLayoutBlock(nodeInfo.referenceNode, MOBILE);
        const desktopBlock = this.getLayoutBlock(nodeInfo.referenceNode, DESKTOP);
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
     * Evaluate which children in nodeAnalysis are related to a given cluster
     * of nodes
     */
    getClusterAnalysis(nodeAnalysis, cluster) {
        const range = this.getNodeClusterRange(cluster.nodes.at(0), cluster.nodes.at(-1));
        const clusterAnalysis = [];
        for (const childAnalysis of nodeAnalysis.children) {
            if (
                childAnalysis.nodeInfos.length &&
                range.comparePoint(childAnalysis.firstNodeInfo.referenceNode, 0) === 0
            ) {
                clusterAnalysis.push(childAnalysis);
            }
        }
        return clusterAnalysis;
    }

    buildCell(nodeAnalysis, cluster, styleContext, isLast = false) {
        const clusterAnalysis = this.getClusterAnalysis(nodeAnalysis, cluster);
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        const cellAnalysis = new NodeAnalysis({
            // TODO EGGMAIL: currently oversimplified identity, to elaborate?
            identity: new ElementIdentity({ tag: "div" }),
            analysis: new Analysis({
                facts: {
                    isHybridFluidCell: true,
                    // TODO EGGMAIL: move refs in identity?
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
        return new NodeAnalysis({
            identity: new ElementIdentity({ tag: "div" }),
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

    buildCellWithOffset(nodeAnalysis, offsetWidth, cluster, styleContext, isLast = false) {
        // TODO EGGMAIL: should a cell + offset be considered differently from a normal cell?
        // It behaves like a row inside a row.
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        const offsetAnalysis = this.buildEmptyCell(offsetWidth);
        const cellAnalysis = this.buildCell(nodeAnalysis, cluster, styleContext);
        const cellWithOffsetAnalysis = new NodeAnalysis({
            identity: new ElementIdentity({ tag: "div" }),
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
