import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { Analysis, ElementIdentity, NodeAnalysis, TextIdentity } from "./node_models";

export class AnalysisPlugin extends Plugin {
    static id = "analysis";
    static dependencies = ["measurementSnapshot", "nodeInfo", "rules"];
    static shared = ["createAnalysisReversedTreeWalker", "createAnalysisTreeWalker"];
    resources = {
        on_build_analysis_tree_handlers: this.buildAnalysisTree.bind(this),
    };

    setup() {
        this.rejectedNodes = new WeakSet();
        this.isAllowedNode = (node) => !this.rejectedNodes.has(node);
        this.needSyntheticNodeAnalysis = new Set();
    }

    createAnalysisTreeWalker() {
        return;
    }

    createAnalysisReversedTreeWalker() {
        return;
    }

    buildAnalysisTree() {
        this.discardIrrelevantNodes();
        this.mergeRedundantNodes();
        this.addSyntheticNodeAnalysis();
        if (this.analysisTree) {
            this.annotateFromChildNodeAnalysis();
            this.annotateFromParentNodeAnalysis();
        }
    }

    discardIrrelevantNodes() {
        const rejectedChildren = new WeakSet();
        const treeWalker = this.createReferenceTreeWalker((node) => {
            if (rejectedChildren.has(node)) {
                return NodeFilter.FILTER_REJECT;
            }
            return NodeFilter.FILTER_ACCEPT;
        });
        let node = treeWalker.root;
        do {
            const nodeInfo = this.getNodeInfo(node);
            if (!this.checkPredicates("should_discard_reference_node_predicates", nodeInfo)) {
                continue;
            }
            this.rejectedNodes.add(node);
            this.processChildNodes(node, (child) => {
                rejectedChildren.add(child);
            });
            nodeInfo.isDiscarded = true;
            console.log("discarded", nodeInfo);
        } while ((node = treeWalker.nextNode()));
    }

    /**
     * Order of operations:
     * - hybrid fluid synthetic nodes creation
     * - treewalking + reverse treewalking
     * - conversion phase => build more specialized blocks/wrap them with MSO entities, etc
     * - render phase should be pretty straightforward from the conversion phase models
     */

    // heuristics suggestion: methodically choose what information is relevant for each semantic node
    // and normalize it in a way that other plugins can use. (not easy because longhand/shorthand stuff in css)
    // discard other specifics (they are still available on the nodeInfo)
    // maybe store tag, styleInfo, attributes and classNames on nodeInfo? to determine

    // A) analysis phase
    // // 0) discard phase (reference treewalk)
    // // 1) absorption phase (reference treewalk) + create analysis tree
    // // 1.5) synthetic wrappers phase (filtered treewalk-y loop on analysis tree)
    // // 2) bottom up analysis (analysis reversed treewalk) + context (register and propagate concerns from different plugins)
    // // 3) top down analysis (analysis treewalk) + context (register and propagate concerns from different plugins)
    // B) conversion phase (analysis treewalk) + create render tree (meet constraint requests)
    // C) render phase (render treewalk)

    // 1) split "discard" concern from "applyStrategy" concern.
    // -- evaluate discard for every node preemptively, and create the set of rejected nodes.

    // probleme: how can I share responsibility here? -> have to avoid any concern that is not "always true"
    // => maybe it's best not to delegate absorption concern, then each plugin can provide the opinion to
    // proceed with absorption or prevent it, node per node?
    // then, default for 1 child is absorption, and "evaluate identity" should deny absorption
    // -- multiple objectives:
    // -- -- deny absorption by parent (if parent allows it)
    // -- -- deny future children absorption (without considering children identities)
    // -- -- provide useful identity info (styleInfo selection, attributes, etc)

    // 2) always evaluate discard one step ahead, so that I know which nodes are actually there
    // -- b) inside loop, the node is never discarded
    // -- -- 1) evaluate identity
    // -- -- -- a) if parent exists and is absorbing and identity allows absorption (no deny) -> merge
    // -- -- -- b) else -> create new NodeAnalysis with this identity
    // -- -- -- -- PROBLEM: how do I create a "CELL" identity from a subset of inline children in a "ROW"?
    // -- -- -- -- SOLUTION: add a grouping pass on some identities that requested it (eg columnsCandidate (row))
    // -- -- -- -- that grouping pass then occurs on the already existing AnalysisTree and can Insert NodeAnalysis that are not related to an existing node
    // -- -- 2) evaluate discard for every child of the current node from the rejected set
    // -- -- -- a) if 1 child and identity (of the "parent") allows it, mark NodeAnalysis as "absorbing"
    // -- -- -- b) else -> remove absorbing (never absorb multiple references into one NodeAnalysis, because
    // -- -- -- -- that would mean multiple "children" positions, more difficult to handle tree navigation)
    buildNodeAnalysis(node, parentNodeAnalysis) {
        const nodeInfo = this.getNodeInfo(node);
        let childNodes, nodeAnalysis;
        if (node.nodeType === Node.TEXT_NODE) {
            const identity = new TextIdentity({ content: node.nodeValue });
            nodeAnalysis = new NodeAnalysis({ identity, nodeInfo, parent: parentNodeAnalysis });
        } else {
            const { identity, analysis } = this.processElementIdentity(
                nodeInfo,
                parentNodeAnalysis
            );
            const parentParsingConstraints = parentNodeAnalysis.analysis.parsingConstraints;
            if (parentNodeAnalysis && !analysis.parsingConstraints.canParentMerge) {
                parentParsingConstraints.canMerge = false;
            }
            nodeAnalysis = parentNodeAnalysis;
            if (parentNodeAnalysis && parentParsingConstraints.canMerge) {
                parentNodeAnalysis.pushNodeInfo(nodeInfo);
                // defaults to keeping the lowest identity as the main identity,
                // written on top of the parent values.
                // merge can be overridden to change that behavior.
                parentNodeAnalysis.identity = identity.merge(parentNodeAnalysis.identity);
                parentNodeAnalysis.analysis.merge(analysis);
            } else {
                nodeAnalysis = new NodeAnalysis({
                    identity,
                    nodeInfo,
                    parent: parentNodeAnalysis,
                    analysis,
                });
            }
            childNodes = this.processChildNodes(node, this.isAllowedNode);
            if (childNodes.length !== 1) {
                nodeAnalysis.analysis.parsingConstraints.canMerge = false;
            }
        }
        if (nodeAnalysis.analysis.parsingConstraints.addSyntheticNodeAnalysis) {
            this.needSyntheticNodeAnalysis.add(nodeAnalysis);
        }
        for (const childNode of childNodes ?? []) {
            this.buildNodeAnalysis(childNode, nodeAnalysis);
        }
        return nodeAnalysis;
    }

    mergeRedundantNodes() {
        const node = this.config.reference;
        if (!this.isAllowedReferenceNode(node) || this.rejectedNodes.has(node)) {
            return;
        }
        this.analysisTree = this.buildNodeAnalysis(node);
    }

    /**
     * some nodeAnalysis children need to be grouped into synthetic
     * containers (eg children of a hybrid fluid row, if a cluster of inline nodes
     * is next to a "block", they all should be wrapped in a "block")
     * it's best to have a separate phase for this to separate it from the merging
     * phase
     */
    addSyntheticNodeAnalysis() {
        for (const nodeAnalysis of [...this.needSyntheticNodeAnalysis]) {
            this.needSyntheticNodeAnalysis.delete(nodeAnalysis);
            this.processThrough("synthetic_node_analysis_processors", nodeAnalysis);
        }
    }

    // TODO EGGMAIL: search and replace all usages of:
    // apply_layout_strategy_overrides
    processElementIdentity(nodeInfo, parentNodeAnalysis) {
        const { identity, analysis } = this.processThrough(
            "element_identity_analysis_processors",
            {
                identity: new ElementIdentity({
                    tag: nodeInfo.referenceNode.tagName,
                    attributes: this.getAttributes(nodeInfo),
                    style: this.getStyleInfo(nodeInfo),
                }),
                analysis: new Analysis({
                    parsingConstraints: { canParentMerge: true, canMerge: true },
                }),
            },
            { nodeInfo, parentNodeAnalysis }
        );
        if (identity.pluginIds.size === 0) {
            identity.pluginIds.add(AnalysisPlugin.id);
        }
        console.log(Array.from(identity.pluginIds).join(", "), nodeInfo);
        return { identity, analysis };
    }

    annotateFromChildNodeAnalysis() {
        return;
    }

    annotateFromParentNodeAnalysis() {
        return;
    }
}

registry.category("mail-html-conversion-core-plugins").add(AnalysisPlugin.id, AnalysisPlugin);
