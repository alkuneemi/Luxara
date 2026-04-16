/**
 * Check whether the given element is inside a social snippet.
 *
 * Social snippets (e.g. `.s_social_media`, `.s_share`) restrict some editor
 * options such as icon background or size customization.
 *
 * @param {HTMLElement} editingElement
 * @returns {boolean} Whether the element is inside a social snippet.
 */
export function isInsideSocialSnippet(editingElement) {
    return Boolean(editingElement.closest(".s_social_media") || editingElement.closest(".s_share"));
}
