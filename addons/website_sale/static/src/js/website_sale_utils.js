import { createElementWithContent } from "@web/core/utils/html";

/**
 * Displays `message` in an alert box at the top of the page if it's a
 * non-empty string.
 *
 * @param {string | null} message
 */
function showWarning(message) {
    if (!message) return;
    document.querySelector('.oe_website_sale')?.querySelector('#data_warning')?.remove();

    const alertDiv = document.createElement('div');
    alertDiv.classList.add('alert', 'alert-danger', 'alert-dismissible');
    alertDiv.role = 'alert';
    alertDiv.id = 'data_warning';
    const closeButton = document.createElement('button');
    closeButton.classList.add('btn-close');
    closeButton.type = 'button'; // Avoid default submit type in case of a form.
    closeButton.dataset.bsDismiss = 'alert';
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    alertDiv.appendChild(closeButton);
    alertDiv.appendChild(messageSpan);
    document.querySelector('.oe_website_sale').prepend(alertDiv);
}

/**
 * Return the selected attribute values from the given container.
 *
 * @param {Element} container the container to look into
 */
function getSelectedAttributeValues(container) {
    return Array.from(container.querySelectorAll(
        'input.js_variant_change:checked, select.js_variant_change'
    )).map(el => parseInt(el.value));
}

/**
 * Update the cart summary.
 *
 * @param {Object} data
 * @return {void}
 */
function updateCartSummary(data) {
    if (data["website_sale.shorter_cart_summary"]) {
        const shorterCartSummaryEl = document.querySelector(".o_wsale_shorter_cart_summary");
        const newShorterCartSummaryEl = createElementWithContent(
            "div",
            data["website_sale.shorter_cart_summary"]
        );
        shorterCartSummaryEl.replaceWith(...newShorterCartSummaryEl.childNodes);
    }
}

/**
 * Extract text content from edit-mode DOM nodes (mostly labels) to feed OWL cart
 * components (cart lines, totals, quick reorder etc).
 *
 * Values come from server-rendered edit-mode templates and are passed as props
 * to preserve partial editability (e.g. customizable labels).
 *
 * @param {HTMLElement} root - Parent element containing edit-mode DOM
 * @param {Object<string, string>} selectors - Mapping of prop keys to CSS selectors
 * @returns {Object<string, string>} Extracted text values
 */
function extractEditModeText(root, selectors) {
    const data = {};

    for (const key in selectors) {
        const node = root.querySelector(selectors[key]);
        if (node) {
            data[key] = node.textContent;
        }
    }

    return data;
}

export default {
    extractEditModeText: extractEditModeText,
    showWarning: showWarning,
    getSelectedAttributeValues: getSelectedAttributeValues,
    updateCartSummary: updateCartSummary,
};
