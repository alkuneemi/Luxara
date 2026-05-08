import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Many2ManySelection extends Interaction {
    static selector = ".s_website_form_m2m_selection";
    dynamicContent = {
        ".dropdown-item": { "t-on-click": this.onOptionClick },
        ".s_website_form_m2m_pill i": { "t-on-click": this.onPillRemove },
    };

    setup() {
        this.selectEl = this.el.querySelector("select.s_website_form_input");
        this.pillsContainer = this.el.querySelector(".s_website_form_m2m_pills_container");
        this.placeholderEl = this.pillsContainer.querySelector(".s_website_form_m2m_placeholder");
        this.elements = new Map();
        this.initiallySelectedOptions = new Map();
        for (const optionEl of this.selectEl.options) {
            const value = optionEl.value;
            const escaped = CSS.escape(value);
            this.elements.set(value, {
                optionEl,
                pillEl: this.pillsContainer.querySelector(
                    `.s_website_form_m2m_pill[data-value="${escaped}"]`
                ),
                checkboxEl: this.el.querySelector(
                    `.dropdown-item[data-value="${escaped}"] input[type=checkbox]`
                ),
            });
            this.initiallySelectedOptions.set(value, optionEl.hasAttribute("selected"));
        }
        this.bsDropdown = window.Dropdown.getOrCreateInstance(this.pillsContainer);
        this.resizeObserver = new ResizeObserver(() => this.bsDropdown.update());
        this.resizeObserver.observe(this.pillsContainer);
        this.registerCleanup(() => {
            this.resizeObserver.disconnect();
            this.bsDropdown.hide();
            this.bsDropdown.dispose();
            for (const [value, selected] of this.initiallySelectedOptions) {
                this.setSelection(value, selected);
            }
        });
    }

    /**
     * Applies the selection state for a given option value across the three
     * linked elements: the hidden `<select>` option, its pill, and its
     * dropdown-item checkbox. Also refreshes the placeholder visibility.
     *
     * @param {string} value option value to update.
     * @param {boolean} selected target selection state.
     * @param {boolean} [moveToEnd=false] when selecting, re-append the pill to
     *      the container so the visible order reflects the order in which the
     *      user picked options.
     */
    setSelection(value, selected, moveToEnd = false) {
        const { optionEl, pillEl, checkboxEl } = this.elements.get(value);
        optionEl.selected = selected;
        pillEl?.classList.toggle("d-none", !selected);
        if (checkboxEl) {
            checkboxEl.checked = selected;
        }
        if (moveToEnd && selected && pillEl) {
            this.pillsContainer.appendChild(pillEl);
        }
        this.placeholderEl.classList.toggle("d-none", this.hasSelection());
    }

    /**
     * @returns {boolean} whether any option is currently selected.
     */
    hasSelection() {
        for (const { optionEl } of this.elements.values()) {
            if (optionEl.selected) {
                return true;
            }
        }
        return false;
    }

    /**
     * @param {Event} ev
     */
    onOptionClick(ev) {
        const dropdownItemEl = ev.currentTarget;
        const checkboxEl = dropdownItemEl.querySelector("input[type=checkbox]");
        this.setSelection(dropdownItemEl.dataset.value, !checkboxEl.checked, true);
        this.selectEl.dispatchEvent(new Event("input", { bubbles: true }));
    }

    /**
     * @param {Event} ev
     */
    onPillRemove(ev) {
        const pillEl = ev.currentTarget.closest(".s_website_form_m2m_pill");
        this.setSelection(pillEl.dataset.value, false);
        this.selectEl.dispatchEvent(new Event("input", { bubbles: true }));
    }
}

registry.category("public.interactions").add("website.many2many_selection", Many2ManySelection);
