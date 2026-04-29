import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";

export class RenderPlugin extends Plugin {
    static id = "render";
    static dependencies = ["analysis"];
    resources = {
        on_build_render_tree_handlers: this.buildRenderTree.bind(this),
        on_render_email_template_handlers: this.renderEmailHtml.bind(this),
    };

    buildRenderTree() {
        const analysisTree = this.getAnalysisTree();
        if (!analysisTree) {
            return;
        }
        // Currently, all my nodes have annotations/facts that concern THEM that were either:
        // -identified
        // -propagated from a descendant or an ancestor
        // these facts should be used to alter what the node itself becomes.
        // these facts could result in the node becoming more than one node.
            // isn't there an issue that these new nodes would require a new analysis phase?
        // 



        // pass 4 / B):
        // iterate over "identity" => identity should be a model which
        // is comprised of every potential part (this is where isolation of concerns ends?)
        
        // per node, allocate a model, related to a template
        // the template has slots, and aggregates all concerns (can be done with xpath if we want to isolate some stuff)
        // complete the model so that every slot has its complete info
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
