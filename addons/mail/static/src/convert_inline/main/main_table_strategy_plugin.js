import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { withSequence } from "@html_editor/utils/resource";
import { Rules } from "../core/rules_models";
import { MainTableLayout, MainTableWrapper } from "./main_table_models";
import { StyleInfo } from "../core/style_models";

export class MainTableStrategyPlugin extends Plugin {
    static id = "mainTableStrategy";
    static dependencies = ["filterContent", "measurementSnapshot", "rules", "style", "vDom"];
    resources = {
        apply_layout_strategy_overrides: withSequence(2, this.applyLayoutStrategy.bind(this)),
        on_reference_content_loaded_handlers: this.identifyLayout.bind(this),
    };

    setup() {
        this.layoutRulesByRef = {
            root: new Rules(),
        };
        this.wrapperRulesByRef = {
            root: new Rules(),
            td: new Rules(),
        };
        this.provideLayoutStyleRules();
        this.provideWrapperStyleRules();
    }

    provideLayoutStyleRules() {
        const root = this.layoutRulesByRef.root.forPlugin(MainTableStrategyPlugin.id);
        root.allow("background-color", {
            when: ({ nodeInfo }) =>
                nodeInfo.referenceNode.matches?.(".o_layout:not(.o_basic_theme)"),
        });
    }

    provideWrapperStyleRules() {
        const root = this.wrapperRulesByRef.root.forPlugin(MainTableStrategyPlugin.id);
        const td = this.wrapperRulesByRef.td.forPlugin(MainTableStrategyPlugin.id);
        root.allow("max-width");
        root.allow(/^margin(-.*)?$/);

        td.allow(/^padding(-.*)?$/);
    }

    identifyLayout() {
        this.layout = this.config.reference.querySelector(".o_layout");
    }

    applyLayoutStrategy(nodeInfo) {
        let hasMainTable = this.detectMainTableLayout(nodeInfo);
        if (hasMainTable) {
            this.buildLayoutFragment(nodeInfo);
        } else if ((hasMainTable = this.detectMainTableWrapper(nodeInfo))) {
            this.buildWrapperFragment(nodeInfo);
        }
        if (hasMainTable) {
            nodeInfo.defineLayoutStrategy({ pluginId: MainTableStrategyPlugin.id });
            return true;
        }
    }

    detectMainTableLayout(nodeInfo) {
        if (this.layout) {
            return nodeInfo.referenceNode === this.layout;
        } else {
            return nodeInfo.referenceNode === this.config.reference;
        }
    }

    detectMainTableWrapper(nodeInfo) {
        return nodeInfo.referenceNode.matches?.(".o_mail_wrapper");
    }

    buildMainTableFragment(nodeInfo, MainTableModel, rulesByRef) {
        const refs = Object.fromEntries(
            Object.entries(rulesByRef).map(([ref, rules]) => [
                ref,
                {
                    style: this.filterStyleInfo(
                        this.getRawStyleInfo(nodeInfo.referenceNode),
                        nodeInfo,
                        rules
                    ),
                },
            ])
        );
        if (rulesByRef === this.layoutRulesByRef) {
            refs.root ??= {};
            const rootStyle = refs.root.style ?? {};
            refs.root.style = this.getBodyGlobalStyleInfo().merge(StyleInfo.from(rootStyle));
        }
        refs.td ??= {};
        const tdStyle = refs.td.style ?? {};
        refs.td.style = this.getBodyTextStyleInfo().merge(StyleInfo.from(tdStyle));
        const vNodes = [];
        this.processChildNodes(nodeInfo.referenceNode, (node) =>
            vNodes.push(this.getNodeInfo(node).vNode)
        );
        const mainTable = new MainTableModel({
            refs,
            childNodes: vNodes,
        });
        nodeInfo.fragment = mainTable.renderToFragment();
    }

    buildLayoutFragment(nodeInfo) {
        this.buildMainTableFragment(nodeInfo, MainTableLayout, this.layoutRulesByRef);
    }

    buildWrapperFragment(nodeInfo) {
        this.buildMainTableFragment(nodeInfo, MainTableWrapper, this.wrapperRulesByRef);
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(MainTableStrategyPlugin.id, MainTableStrategyPlugin);
