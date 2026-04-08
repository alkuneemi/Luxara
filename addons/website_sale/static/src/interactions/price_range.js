import { Interaction } from '@web/public/interaction';
import { redirect } from '@web/core/utils/urls';
import { registry } from '@web/core/registry';

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
        if (isOffcanvas) {
            const offcanvas = document.querySelector('.o_website_offcanvas');
            const offcanvasResponse = await fetch(`${url.pathname}?${searchParams.toString()}`);
            const offcanvaData = await offcanvasResponse.text();
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = offcanvaData;

            const newOffcanvas = tempDiv.querySelector('.o_website_offcanvas').innerHTML;
            const shopPageEl = document.querySelector('.o_wsale_products_page');
            this.services['public.interactions'].stopInteractions(shopPageEl);
            offcanvas.innerHTML = newOffcanvas;
            this.services['public.interactions'].startInteractions(shopPageEl);

            searchParams.set('is_ajax_count', 'true');
            const countResponse = await fetch(`${url.pathname}?${searchParams.toString()}`);
            const countData = await countResponse.json();

            const applyBtn = document.querySelector('#o_wsale_offcanvas #o_wsale_apply_filters_btn');
            if (applyBtn) {
                applyBtn.textContent = `Apply Filters (${countData.count})`;
            }
        } else {
            const product_list_div = document.querySelector('.o_wsale_products_grid_table_wrapper');
            if (product_list_div) {
                product_list_div.classList.add('opacity-50');
            }
            redirect(`${url.pathname}?${searchParams.toString()}`);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.price_range', PriceRange);
