import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";
import { TagsMany2Many } from "./tags_many2many";

export const PRODUCT_TEMPLATE_OPTION_SELECTOR = ".o_wsale_product_page:has(.variant_attribute)";

export class ProductTemplateOption extends BaseOptionComponent {
    static id = "product_template_option";
    static template = "website_sale.ProductTemplateOption";
    static components = { TagsMany2Many };

    setup() {
        super.setup();
        this.domState = useDomState(async (el) => {
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;

            return {
                templateId,
            };
        });
    }

    applyTags(newTags) {
        const tagListEl = this.env.getEditingElement().querySelector(".o_product_tags");
        const oldTags = [];
        for (const child of tagListEl.children) {
            const tagId = child.querySelector('[data-oe-model="product.tag"]')?.dataset.oeId;
            if (tagId) {
                oldTags.push({ id: parseInt(tagId) });
            }
        }
        const addedTags = newTags.filter(
            (tag) => !oldTags.some((current) => current.id === tag.id)
        );
        const removedTags = oldTags.filter(
            (current) => !newTags.some((tag) => tag.id === current.id)
        );

        for (const tag of removedTags) {
            const tagEl = tagListEl.querySelector(
                `a:has(.o_wsale_product_tag [data-oe-id="${tag.id}"]), a:has(.o_wsale_product_tag_image[data-oe-id="${tag.id}"])`
            );
            tagEl?.remove();
        }

        for (const tag of addedTags) {
            if (!tagListEl.children?.length) {
                tagListEl.className =
                    "o_product_tags o_field_tags d-flex flex-wrap align-items-center gap-2 mb-2 mt-1";
            }

            const newTagLink = document.createElement("a");
            newTagLink.className = "text-decoration-none d-inline-block";
            newTagLink.href = `/shop?tags=${tag.id}`;

            const newTagEl = document.createElement("span");
            newTagEl.className = "o_wsale_product_tag position-relative order-1 py-1 px-2";

            const newTagBackground = document.createElement("span");
            newTagBackground.className = "position-absolute top-0 start-0 w-100 h-100 rounded";
            newTagBackground.style = "background-color: #3C3C3C; opacity: .2;";

            const newTagName = document.createElement("span");
            newTagName.className = "text-nowrap small";
            newTagName.style = "color: #3C3C3C;";
            newTagName.dataset.oeModel = "product.tag";
            newTagName.dataset.oeId = tag.id;
            newTagName.textContent = tag.name;

            newTagEl.appendChild(newTagBackground);
            newTagEl.appendChild(newTagName);
            newTagLink.appendChild(newTagEl);
            tagListEl.appendChild(newTagLink);
        }
    }
}

registry.category("website-options").add(ProductTemplateOption.id, ProductTemplateOption);
