import { startInteractions } from "@web/../tests/public/helpers";
import { getStructureSnippet } from "../builder/website_helpers";

/**
 * @param {string | string[]} snippetName
 * @param {{
 *   withImgSrc?: boolean,
 *   processHTML?: function(string): string,
 *   waitForStart?: boolean,
 *   editMode?: boolean,
 *   translateMode?: boolean,
 * }} options
 */
export async function startInteractionsWithSnippet(snippetName, options = {}) {
    const { withImgSrc, processHTML, ...startOptions } = options;
    let html = "";
    const snippetNames = Array.isArray(snippetName) ? snippetName : [snippetName];
    for (const name of snippetNames) {
        const el = await getStructureSnippet(name, withImgSrc);
        html += el.outerHTML;
    }
    if (typeof processHTML === "function") {
        html = processHTML(html);
    }
    return startInteractions(html, startOptions);
}
