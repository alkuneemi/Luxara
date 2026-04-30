import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { Analysis, ElementIdentity, NodeAnalysis, TextIdentity } from "./node_models";

/**
 * This plugin handles 2 conversion phases:
 * 1) identify semantic grouping boundaries
 * // a) discard pass to remove irrelevant nodes
 * // b) absorption pass to eliminate containers overlapping their content (no visual value)
 * // c) add synthetic nodes pass to group some content inside a container that is implied by css only
 * 2) propagate constraints from these groupings to annotate them:
 * // a) bottom up analysis (descendants propagate constraints and information to their ancestors)
 * // b) top down analysis (ancestors propagate constraints and information to their descendants)
 */
export class AnalysisPlugin extends Plugin {
    static id = "analysis";
    static dependencies = ["measurementSnapshot", "node", "rules"];
    static shared = ["getAnalysisTree"];
    resources = {
        on_build_analysis_tree_handlers: this.buildAnalysisTree.bind(this),
    };

    setup() {
        this.rejectedNodes = new WeakSet();
        this.isAllowedNode = (node) => !this.rejectedNodes.has(node);
        this.needSyntheticNodeAnalysis = new Set();
    }

    getAnalysisTree() {
        return this.analysisTree;
    }

    buildAnalysisTree() {
        this.discardIrrelevantNodes();
        this.mergeRedundantNodes();
        this.addSyntheticNodeAnalysis();
        if (this.analysisTree) {
            this.annotateFromChildNodeAnalysis(this.analysisTree);
            this.annotateFromParentNodeAnalysis(this.analysisTree);
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
            if (!this.checkPredicates("should_discard_reference_node_predicates", node)) {
                continue;
            }
            this.rejectedNodes.add(node);
            this.processChildNodes(node, (child) => {
                rejectedChildren.add(child);
            });
            console.log("discarded", node);
        } while ((node = treeWalker.nextNode()));
    }

    // -- multiple objectives:
    // -- -- deny absorption by parent (if parent allows it)
    // -- -- deny future children absorption (without considering children identities)
    // -- -- provide useful identity info (styleInfo selection, attributes, etc)
    buildNodeAnalysis(node, parentNodeAnalysis) {
        let childNodes, nodeAnalysis;
        if (node.nodeType === Node.TEXT_NODE) {
            const identity = new TextIdentity({ content: node.nodeValue });
            nodeAnalysis = new NodeAnalysis({
                identity,
                referenceNode: node,
                parent: parentNodeAnalysis,
            });
        } else {
            const { identity, analysis } = this.processElementIdentity(node, parentNodeAnalysis);
            const parentParsingFacts = parentNodeAnalysis.analysis.parsingFacts;
            if (parentNodeAnalysis && !analysis.parsingFacts.canParentMerge) {
                parentParsingFacts.canMerge = false;
            }
            nodeAnalysis = parentNodeAnalysis;
            if (parentNodeAnalysis && parentParsingFacts.canMerge) {
                parentNodeAnalysis.pushReferenceNode(node);
                // defaults to keeping the lowest identity as the main identity,
                // written on top of the parent values.
                // merge can be overridden to change that behavior.
                parentNodeAnalysis.identity = identity.merge(parentNodeAnalysis.identity);
                parentNodeAnalysis.analysis.merge(analysis);
            } else {
                nodeAnalysis = new NodeAnalysis({
                    identity,
                    referenceNode: node,
                    parent: parentNodeAnalysis,
                    analysis,
                });
            }
            childNodes = this.processChildNodes(node, this.isAllowedNode);
            if (childNodes.length !== 1) {
                nodeAnalysis.analysis.parsingFacts.canMerge = false;
            }
        }
        if (nodeAnalysis.analysis.parsingFacts.addSyntheticNodeAnalysis) {
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
            // IMPORTANT: if nodeAnalysis is replaced/removed, all of its children
            // should be given a new parent, this is not a phase where nodes
            // can be discarded.
            this.processThrough("synthetic_node_analysis_processors", nodeAnalysis);
        }
    }

    // TODO EGGMAIL: search and replace all usages of:
    // apply_layout_strategy_overrides
    processElementIdentity(referenceNode, parentNodeAnalysis) {
        const { identity, analysis } = this.processThrough(
            "element_identity_analysis_processors",
            {
                identity: new ElementIdentity({
                    tag: referenceNode.tagName,
                    attributes: this.getAttributes(referenceNode),
                    style: this.getStyleInfo(referenceNode),
                }),
                analysis: new Analysis({
                    parsingFacts: { canParentMerge: true, canMerge: true },
                }),
            },
            { referenceNode, parentNodeAnalysis }
        );
        if (identity.pluginIds.size === 0) {
            identity.pluginIds.add(AnalysisPlugin.id);
        }
        console.log(Array.from(identity.pluginIds).join(", "), referenceNode);
        return { identity, analysis };
    }

    /**
     * Allow descendants to propagate facts to their ancestors through constraints
     * callbacks
     */
    annotateFromChildNodeAnalysis(nodeAnalysis) {
        const childConstraints = [];
        for (const child of nodeAnalysis.children) {
            childConstraints.concat(this.annotateFromChildNodeAnalysis(child));
        }
        const propagatedConstraints = [];
        for (const constraint of childConstraints) {
            // `constraint` API => return object with "shouldPropagate"+ "facts"
            const annotations = constraint(nodeAnalysis);
            if (annotations.shouldPropagate) {
                propagatedConstraints.push(constraint);
            }
            for (const [fact, value] of Object.entries(annotations.facts ?? {})) {
                if (!this.delegateTo("merge_fact_overrides", { nodeAnalysis, fact, value })) {
                    // TODO EGGMAIL: better default action for merging current fact with a new value
                    // should we save descendantFacts separately from localFacts?
                    // TODO EGGMAIL: here a fact from a descendant is directly applied to the current
                    // nodeAnalysis, maybe it makes sense to aggregate all descendant facts, then apply
                    // the final result on the current nodeAnalysis?
                    nodeAnalysis.analysis.facts[fact] = value;
                }
            }
        }
        return nodeAnalysis.constraintsForAncestors.concat(propagatedConstraints);
    }

    /**
     * Allow ancestors to propagate facts to their descendants through constraints
     * callbacks
     */
    annotateFromParentNodeAnalysis(nodeAnalysis, constraints = []) {
        const propagatedConstraints = [];
        for (const constraint of constraints) {
            const annotations = constraint(nodeAnalysis);
            if (annotations.shouldPropagate) {
                propagatedConstraints.push(constraint);
            }
            for (const [fact, value] of Object.entries(annotations.facts ?? {})) {
                if (!this.delegateTo("merge_fact_overrides", { nodeAnalysis, fact, value })) {
                    nodeAnalysis.analysis.facts[fact] = value;
                }
            }
        }
        for (const child of nodeAnalysis.children) {
            this.annotateFromParentNodeAnalysis(
                child,
                nodeAnalysis.constraintsForDescendants.concat(propagatedConstraints)
            );
        }
    }
}

registry.category("mail-html-conversion-core-plugins").add(AnalysisPlugin.id, AnalysisPlugin);
