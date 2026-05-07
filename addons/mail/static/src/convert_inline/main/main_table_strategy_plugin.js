import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { withSequence } from "@html_editor/utils/resource";
import { Rules } from "../core/rules_models";
import { MainTableLayout, MainTableWrapper } from "./main_table_models";
import { StyleInfo } from "../core/style_models";

export class MainTableStrategyPlugin extends Plugin {
    static id = "mainTableStrategy";
    static dependencies = [
        "filterContent",
        "measurementSnapshot",
        "rules",
        "style",
        "referenceNode",
    ];
    resources = {
        apply_layout_strategy_overrides: withSequence(2, this.applyLayoutStrategy.bind(this)),
        element_identity_analysis_processors: withSequence(
            2,
            this.analyzeElementIdentity.bind(this)
        ),
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
            when: ({ referenceNode }) => referenceNode.matches?.(".o_layout:not(.o_basic_theme)"),
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

    /**
     * TODO EGGMAIL: mutually exclusive identities? Does having this identity
     * prevent another plugin from claiming another identity? To think about.
     * evaluate withSequence
     */
    analyzeElementIdentity({ identity, analysis }, { referenceNode }) {
        if (analysis.isFrozen) {
            return;
        }
        let hasMainTable = this.detectMainTableLayout(referenceNode);
        if (hasMainTable) {
            analysis.facts.isMainTableLayout = true;
        } else if ((hasMainTable = this.detectMainTableWrapper(referenceNode))) {
            analysis.facts.isMainTableWrapper = true;
        }
        if (hasMainTable) {
            analysis.freeze();
            Object.assign(analysis.parsingFacts, {
                canMerge: false,
                canParentMerge: false,
            });
            identity.pluginIds.add(MainTableStrategyPlugin.id);
        }
    }

    applyLayoutStrategy(referenceNode) {
        let hasMainTable = this.detectMainTableLayout(referenceNode);
        if (hasMainTable) {
            this.buildLayoutFragment(referenceNode);
        } else if ((hasMainTable = this.detectMainTableWrapper(referenceNode))) {
            this.buildWrapperFragment(referenceNode);
        }
        if (hasMainTable) {
            referenceNode.defineLayoutStrategy({ pluginId: MainTableStrategyPlugin.id });
            return true;
        }
    }

    detectMainTableLayout(referenceNode) {
        if (this.layout) {
            return referenceNode === this.layout;
        } else {
            return referenceNode === this.config.reference;
        }
    }

    detectMainTableWrapper(referenceNode) {
        return referenceNode.matches?.(".o_mail_wrapper");
    }

    buildMainTableFragment(referenceNode, MainTableModel, rulesByRef) {
        const refs = Object.fromEntries(
            Object.entries(rulesByRef).map(([ref, rules]) => [
                ref,
                {
                    style: this.filterStyleInfo(
                        this.getRawStyleInfo(referenceNode),
                        referenceNode,
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
        // TODO REMOVE VNODE:
        this.processChildNodes(referenceNode, (node) => vNodes.push(node.vNode));
        const mainTable = new MainTableModel({
            refs,
            childNodes: vNodes,
        });
        referenceNode.fragment = mainTable.renderToFragment();
    }

    buildLayoutFragment(referenceNode) {
        this.buildMainTableFragment(referenceNode, MainTableLayout, this.layoutRulesByRef);
    }

    buildWrapperFragment(referenceNode) {
        this.buildMainTableFragment(referenceNode, MainTableWrapper, this.wrapperRulesByRef);
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(MainTableStrategyPlugin.id, MainTableStrategyPlugin);
