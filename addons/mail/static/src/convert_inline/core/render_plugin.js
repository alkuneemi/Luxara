import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";

/**
 * This plugin handles 2 conversion phases:
 * 1) refine the identity of semantic nodes from the analysis plugin
 * // a) alter/replace node identities to fulfill constraints for every node
 * 2) render the final email html tree
 * // a) render each identity to create the final html tree
 */
export class RenderPlugin extends Plugin {
    static id = "render";
    static dependencies = ["analysis"];
    resources = {
        on_build_render_tree_handlers: this.buildRenderTree.bind(this),
        on_render_email_template_handlers: this.renderEmailHtml.bind(this),
    };

    buildRenderTree() {
        // My idea right now:
        // identity starts as the simple element transcription
        // analysis accumulates facts during various kind of passes
        // after every node has its facts updated, the render_plugin goes through the tree
        // and fulfill all facts
        // // -> all facts are "requests" to be fulfilled by the identity, if the identity changes, it should ensure
        // // all facts are fulfilled.
        // TODO:
        // cleanup comments to extract useful ideas and remove other stuff
        // decide on identity general API
        // merge LayoutModel and Identity models, makes no sense to have both
        // an identity can contain others => we are really into the LayoutModel territory here
        // an identity can also have multiple slots instead of sub-identities (do I keep such flexibility?)
        // the "render" method of an Identity should take care of handling its subtree
        // the Identity subtree relates to only one NodeAnalysis, which was one render intention
        const analysisTree = this.getAnalysisTree();
        if (!analysisTree) {
            return;
        }
        this.refineIdentity(analysisTree);
    }

    refineIdentity(nodeAnalysis) {
        // keep original identity (inside nodeAnalysis) untouched during the
        // whole process, but the current identity can be used
        nodeAnalysis.identity = this.processThrough(
            "refine_identity_processors",
            nodeAnalysis.identity,
            { nodeAnalysis }
        );
        for (const childAnalysis of nodeAnalysis.children) {
            this.refineIdentity(childAnalysis);
        }
    }

    ensureTemplateContent(template) {
        if (!template.content.firstChild) {
            const paragraph = this.config.referenceDocument.createElement("P");
            const br = this.config.referenceDocument.createElement("BR");
            paragraph.append(br);
            template.content.appendChild(paragraph);
        }
    }

    renderEmailHtml(template) {
        // TODO EGGMAIL: use the LayoutModel tree to render the final email
        this.ensureTemplateContent(template);
    }
}

registry.category("mail-html-conversion-core-plugins").add(RenderPlugin.id, RenderPlugin);
