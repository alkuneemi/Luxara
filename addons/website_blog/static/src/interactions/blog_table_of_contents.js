import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class BlogTableOfContents extends Interaction {
    static selector = ".o_wblog_toc";

    setup() {
        this.navEl = this.el.querySelector(".o_wblog_toc_nav");
        this.contentEl = document.querySelector("#o_wblog_post_content .o_wblog_post_content_field");
        if (!this.navEl || !this.contentEl) {
            return;
        }
        this.offsets = [];
        this.targets = [];
        this.activeTarget = null;
        this._hasScrollListener = false;
    }

    start() {
        if (!this.navEl || !this.contentEl) {
            return;
        }

        this.generateTOC();
        this._updateTOCBehaviour();
    }

    generateTOC() {
        const headingEls = this.contentEl.querySelectorAll("h1, h2, h3, h4, h5, h6");
        this.navEl.innerHTML = "";
        this.targets = [];
        if (!headingEls.length) {
            return;
        }

        const listGroupEl = document.createElement("div");
        listGroupEl.className = "list-group list-group-flush position-relative o_not_editable";
        listGroupEl.setAttribute("contenteditable", "false");
        // Track ancestor headings to derive a display level that never grows
        // by more than 1 between consecutive headings, regardless of the raw
        // h1..h6 jumps in the markup.
        const levelStack = [];
        // Ephemeral fallback ids for posts whose content pre-dates the
        // editor-time normalization. These are never persisted; once the post
        // is opened in the editor and saved the stable ids replace them.
        const usedIds = new Set();

        headingEls.forEach((headingEl, i) => {
            if (!headingEl.id || usedIds.has(headingEl.id)) {
                headingEl.id = `table_of_content_heading_1_${i + 1}`;
            }
            usedIds.add(headingEl.id);
            const htmlLevel = parseInt(headingEl.tagName[1]);
            while (levelStack.length && levelStack.at(-1).htmlLevel >= htmlLevel) {
                levelStack.pop();
            }
            const level = levelStack.length ? levelStack.at(-1).level + 1 : 0;
            levelStack.push({ htmlLevel, level });
            const linkEl = document.createElement("a");
            linkEl.href = `#${headingEl.id}`;
            linkEl.textContent = headingEl.textContent.trim();
            linkEl.className = `list-group-item list-group-item-action o_wblog_toc_link o_wblog_toc_link_${level} bg-transparent border-0 position-relative small`;
            linkEl.classList.add("o_not_editable");
            linkEl.setAttribute("contenteditable", "false");

            listGroupEl.appendChild(linkEl);
            this.targets.push(`#${headingEl.id}`);
        });

        this.navEl.appendChild(listGroupEl);
        this.waitFor(this.services["public.interactions"].startInteractions(listGroupEl));
        this.refresh();
    }

    _updateTOCBehaviour() {
        if (!this.targets.length) {
            this.el.classList.add("d-none");
            this.offsets = [];
            this.activeTarget = null;
            return;
        }
        this.el.classList.remove("d-none");
        if (this.el.classList.contains("o_wblog_toc_mobile")) {
            return;
        }
        if (!this._hasScrollListener) {
            this.addListener(window, "scroll", this.process.bind(this));
            this._hasScrollListener = true;
        }
        // Delay initial process to ensure layout is complete
        setTimeout(() => this.process(), 100);
    }

    refresh() {
        this.offsets = this.targets.map(target => {
            const el = document.querySelector(target);
            return el ? el.getBoundingClientRect().top + window.scrollY : 0;
        });
    }

    process() {
        if (!this.offsets.length) {
            return;
        }

        const scrollTop = window.scrollY + 120;

        if (scrollTop < this.offsets[0]) {
            this.activate(this.targets[0]);
            return;
        }

        for (let i = this.offsets.length; i--;) {
            if (scrollTop >= this.offsets[i]) {
                if (this.activeTarget !== this.targets[i]) {
                    this.activate(this.targets[i]);
                }
                return;
            }
        }
    }

    activate(target) {
        this.activeTarget = target;
        this.clear();
        const linkEl = this.navEl.querySelector(`[href="${target}"]`);
        if (linkEl) {
            linkEl.classList.add("active", "ps-3");
        }
    }

    clear() {
        for (const link of this.navEl.querySelectorAll(".list-group-item")) {
            link.classList.remove("active", "ps-3");
        }
    }
}

registry.category("public.interactions").add("website_blog.toc", BlogTableOfContents);
registry.category("public.interactions.edit").add("website_blog.toc", { Interaction: BlogTableOfContents });
