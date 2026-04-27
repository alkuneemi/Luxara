import { Interaction } from '@web/public/interaction';
import { redirect } from '@web/core/utils/urls';
import { registry } from '@web/core/registry';
import { updateShopContent } from "./shop_ajax";

export class PriceRange extends Interaction {
    static selector = '#o_wsale_price_range_option';
    dynamicContent = {
        'input[type="range"]': { 't-on-newRangeValue': this.onPriceRangeSelected },
    };

    /**
     * @param {Event} ev
     */
    async onPriceRangeSelected(ev) {
        const range = ev.currentTarget;
        const url = new URL(range.dataset.url, window.location.origin);
        const searchParams = url.searchParams;
        if (parseFloat(range.min) !== range.valueLow) {
            searchParams.set("min_price", range.valueLow);
        }
        if (parseFloat(range.max) !== range.valueHigh) {
            searchParams.set("max_price", range.valueHigh);
        }
        const isOffcanvas = !!ev.currentTarget.closest('#o_wsale_offcanvas');

        const productGridWrapper = document.querySelector('.o_wsale_products_grid_table_wrapper');
        if (productGridWrapper) productGridWrapper.classList.add('opacity-50');

        if (isOffcanvas) {
            await updateShopContent({
                url,
                searchParams,
                services: this.services,
            });
        }else {
            redirect(`${url.pathname}?${searchParams.toString()}`);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.price_range', PriceRange);
