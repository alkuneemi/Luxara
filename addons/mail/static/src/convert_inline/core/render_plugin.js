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
        // case study: background color + color filter => should apply the same logic as a normal
        // filter? => if the logic is to create a new attachment. If it uses browser rendering
        // capabilities, then it won't work

        // honestly what's best for me right now:
        // add template wrapper capabilities to tif-telse mso nodes and render a custom mso template
        // have a table replaces div template for all cases where mso requires a table instead of a div
        // I don't know any other cases right now
        // ideally, facts already migrated on the correct node, allowing to apply the table or the conditional
        // mso stuff directly on that node, and we should have all facts necessary to render that node as
        // its alternative way by MSO => I can do it by setting a subtree option, and every subnode has MSO options
        // if necessary in this case
        // I think right now the analysis parsing solves most issues for me
        // => about tables
        // normally, a table will ask that its direct container is not a table => if it is, we create a row + td to wrap
        // it => becomes legal again

        // Currently, all my nodes have annotations/facts that concern THEM that were either:
        // -identified
        // -propagated from a descendant or an ancestor
        // these facts should be used to alter what the node itself becomes.
        // eg a container becomes a table or has to be wrapped in one
        // a node could need an alternative MSO representation
        // idea:
        // Create a new tree where each node can have an associated rendering template
        // -> button node can become => MSO comment (if mso / MSO BUTTON / endif / if !mso) buttonNode w. model + endif mso

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
