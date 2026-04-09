import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { zip } from "@web/core/utils/arrays";
import {
    HybridFluidCell,
    HybridFluidCellWithOffset,
    HybridFluidEmptyCell,
    HybridFluidRow,
} from "./hybrid_fluid_models";
import { DIMENSIONS } from "../hooks";

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
        apply_layout_strategy_overrides: this.applyLayoutStrategy.bind(this),
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

    addSyntheticNodeAnalysis(nodeAnalysis) {
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
     * Attempt1:
     * apply strategy on ROW element, and use COL elements as Cells
     * don't absorb nodes above, and don't absorb col elements
     * TODO EGGMAIL: reevaluate absorption
     */
    applyLayoutStrategy(nodeInfo) {
        if (!this.detectHybridFluidLayout(nodeInfo)) {
            // detect hybrid fluid "rows"
            // -> detect a band with multiple clusters inside a block
            // -> look in mobile mode, the amount of bands should be different
            // -> should not be captured by table, since the table strictly verifies
            // that the amount of bands is the same
            return;
        }
        this.buildFragment(nodeInfo);
        nodeInfo.defineLayoutStrategy({ pluginId: HybridFluidStrategyPlugin.id });
        return true;
    }

    /**
     * TODO EGGMAIL: can I get an hybrid fluid row with only inline children? to investigate
     */
    detectHybridFluidLayout(nodeInfo) {
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

    buildCell(cluster, styleContext, isLast = false) {
        const vNodes = cluster.nodes.map((node) => this.getNodeInfo(node).vNode);
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        return new HybridFluidCell({
            childNodes: vNodes,
            refs: {
                root: { style: { "max-width": `${clusterWidth}px` } },
                styleContext,
            },
        });
    }

    buildEmptyCell(width) {
        return new HybridFluidEmptyCell({
            refs: {
                root: { style: { "max-width": `${width}px` } },
            },
        });
    }

    buildCellWithOffset(offsetWidth, cluster, styleContext, isLast = false) {
        const clusterWidth = cluster.rect.width - (isLast ? ZOOM_WIDTH_CORRECTION : 0);
        const offset = this.buildEmptyCell(offsetWidth);
        const cell = this.buildCell(cluster, styleContext);
        return new HybridFluidCellWithOffset({
            cell,
            offset,
            refs: {
                root: { style: { "max-width": `${offsetWidth + clusterWidth}px` } },
            },
        });
    }

    buildFragment(nodeInfo) {
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
            const row = new HybridFluidRow();
            rows.push(row);
            let prevCluster;
            if (band.clusters.length > 0) {
                prevCluster = band.clusters[0];
                const isLast = band.clusters.length === 1;
                if (!this.isZero(desktopBlock.padding.left)) {
                    const offsetWidth = desktopBlock.padding.left;
                    row.addCell(
                        this.buildCellWithOffset(offsetWidth, prevCluster, styleContext, isLast)
                    );
                } else {
                    row.addCell(this.buildCell(prevCluster, styleContext, isLast));
                }
            }
            for (let i = 1; i < band.clusters.length; i++) {
                const cluster = band.clusters[i];
                const gap = this.gapX(prevCluster.rect, cluster.rect);
                const isLast = i === band.clusters.length - 1;
                if (gap > 0) {
                    row.addCell(this.buildCellWithOffset(gap, cluster, styleContext, isLast));
                } else {
                    row.addCell(this.buildCell(cluster, styleContext, isLast));
                }
                prevCluster = cluster;
            }
            if (!this.isZero(desktopBlock.padding.right)) {
                row.addCell(this.buildEmptyCell(desktopBlock.padding.right));
            }
        }
        const fragment = this.config.referenceDocument.createDocumentFragment();
        const templateNode = this.cloneReferenceNode(nodeInfo);
        templateNode.append(...rows.map((row) => row.renderToFragment()));
        fragment.append(templateNode);
        nodeInfo.fragment = fragment;
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(HybridFluidStrategyPlugin.id, HybridFluidStrategyPlugin);
