import { patch } from "@web/core/utils/patch";
import { ProductPage } from "@website_sale/interactions/product_page";

patch(ProductPage.prototype, {
    async _onChangeCombination(ev, parent, combination) {
        await super._onChangeCombination(ev, parent, combination);

        if (!combination.extra_fields_html) {
            return;
        }

        const parser = new DOMParser();
        const doc = parser.parseFromString(combination.extra_fields_html, "text/html");

        const accordionEl = document.querySelector("#product_accordion");
        if (accordionEl) {
            const newAccordion = doc.querySelector("#product_accordion");
            if (!newAccordion) return;

            const openIds = [...accordionEl.querySelectorAll(".accordion-collapse.show")]
                .map(el => el.id)
                .filter(Boolean);

            accordionEl.insertAdjacentHTML("afterend", newAccordion.outerHTML);
            accordionEl.remove();

            const replacedAccordion = document.querySelector("#product_accordion");
            if (!replacedAccordion) return;

            openIds.forEach(id => {
                const collapseEl = replacedAccordion.querySelector(`#${id}`);
                if (collapseEl) {
                    collapseEl.classList.add("show");
                    const btn = replacedAccordion.querySelector(
                        `[data-bs-target="#${id}"]`
                    );
                    if (btn) {
                        btn.classList.remove("collapsed");
                        btn.setAttribute("aria-expanded", "true");
                    }
                }
            });

            if (!openIds.length) {
                const firstItem = replacedAccordion.querySelector(".accordion-item");
                if (firstItem) {
                    const btn = firstItem.querySelector(".accordion-button");
                    const collapse = firstItem.querySelector(".accordion-collapse");
                    if (btn && collapse) {
                        btn.classList.remove("collapsed");
                        btn.setAttribute("aria-expanded", "true");
                        collapse.classList.add("show");
                    }
                }
            }

            replacedAccordion.classList.remove("o_accordion_not_initialized");
            return;
        }

        const specSection = document.querySelector("#product_full_spec");
        if (specSection) {
            const newSection = doc.querySelector("#product_full_spec");
            if (newSection) {
                specSection.outerHTML = newSection.outerHTML;
            }
            return;
        }

        const newPtalRows = doc.querySelectorAll("tr[data-ptal-id]");
        for (const newRow of newPtalRows) {
            const ptalId = newRow.dataset.ptalId;
            const liveRow = document.querySelector(`tr[data-ptal-id="${ptalId}"]`);
            if (liveRow) {
                const newValueTd = newRow.querySelectorAll("td")[1];
                const liveValueTd = liveRow.querySelectorAll("td")[1];
                if (newValueTd && liveValueTd) {
                    liveValueTd.innerText = newValueTd.innerText;
                }
            }
        }

        const newAttrRows = doc.querySelectorAll("tr[data-attribute-id]");
        for (const newRow of newAttrRows) {
            const attrId = newRow.dataset.attributeId;
            const liveRow = document.querySelector(`tr[data-attribute-id="${attrId}"]`);
            if (liveRow) {
                const newValueTd = newRow.querySelectorAll("td")[1];
                const liveValueTd = liveRow.querySelectorAll("td")[1];
                if (newValueTd && liveValueTd) {
                    liveValueTd.innerText = newValueTd.innerText;
                }
            }
        }

        const newRows = doc.querySelectorAll("tr[data-extra-field-id]");
        for (const newRow of newRows) {
            const fieldId = newRow.dataset.extraFieldId;
            const liveRow = document.querySelector(`tr[data-extra-field-id="${fieldId}"]`);
            if (liveRow) {
                const newValueTd = newRow.querySelectorAll("td")[1];
                const liveValueTd = liveRow.querySelectorAll("td")[1];
                if (newValueTd && liveValueTd) {
                    liveValueTd.innerText = newValueTd.innerText;
                }
            }
        }

        const liveExtraRows = document.querySelectorAll("tr[data-extra-field-id]");
        for (const liveRow of liveExtraRows) {
            const fieldId = liveRow.dataset.extraFieldId;
            const newRow = doc.querySelector(`tr[data-extra-field-id="${fieldId}"]`);
            liveRow.style.display = newRow ? "" : "none";
        }
    },
});
