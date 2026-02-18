import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

export class LayoutStrategyPlugin extends Plugin {
    static id = "layoutStrategy";
    static dependencies = ["measurementSnapshot", "rules", "vDom"];
    resources = {
        apply_layout_strategy_overrides: withSequence(1, this.applyDiscardStrategy.bind(this)),
        on_apply_layout_strategies_handlers: this.applyLayoutStrategies.bind(this),
    };

    applyDiscardStrategy(nodeInfo) {
        if (!this.checkPredicates("should_use_discard_strategy_predicates", nodeInfo)) {
            return;
        }
        nodeInfo.defineLayoutStrategy({ isDiscarded: true });
        return true;
    }

    applyLayoutStrategies() {
        // TODO EGGMAIL: create a tree walker to go over every node in the reference
        // every node should have a "strategy" resulting in a fragment, even if
        // it's ignore/do nothing/skip descendants
        // treeWalker could/should ignore descendants of nodes where the strategy
        // is to ignore descendants
        // review current rendering loop and how it applies fragments
        const rejectedNodes = new WeakSet();
        const treeWalker = this.createReferenceTreeWalker((node) => {
            if (rejectedNodes.has(node)) {
                // TODO EGGMAIL: evaluate if we should apply the Reject strategy
                // on rejectedNodes instead of rejecting them here?
                // or we can just ignore nodes without a strategy during vdom
                return NodeFilter.FILTER_REJECT;
            }
            return NodeFilter.FILTER_ACCEPT;
        });
        let node = treeWalker.root;
        do {
            const nodeInfo = this.getNodeInfo(node);
            this.applyLayoutStrategy(nodeInfo);
            if (nodeInfo.isDiscarded) {
                this.processChildNodes(node, (child) => {
                    rejectedNodes.add(child);
                });
            }
        } while ((node = treeWalker.nextNode()));
    }

    applyLayoutStrategy(nodeInfo) {
        if (!nodeInfo.hasLayoutStrategy) {
            if (!this.delegateTo("apply_layout_strategy_overrides", nodeInfo)) {
                this.applyStyleRules(nodeInfo.fragment.firstElementChild, nodeInfo);
                // Define default layout strategy (use an exact clone in the final render)
                nodeInfo.defineLayoutStrategy({ pluginId: LayoutStrategyPlugin.id });
            }
            console.log(nodeInfo.isDiscarded ? "discarded" : nodeInfo.pluginId, nodeInfo);
        }
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(LayoutStrategyPlugin.id, LayoutStrategyPlugin);
