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

        const productGridWrapper = document.querySelector('.o_wsale_products_grid_table_wrapper');
        if (productGridWrapper) productGridWrapper.classList.add('opacity-50');

        if (isOffcanvas) {
            searchParams.set('is_ajax', 'true');
            const response = await fetch(`${url.pathname}?${searchParams.toString()}`);
            searchParams.delete('is_ajax');
            const data = await response.json();
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = data.html;

            const newProductsGrid = tempDiv.querySelector('.o_wsale_products_grid_table');
            const currentProductsGrid = document.querySelector('.o_wsale_products_grid_table');
            if (currentProductsGrid && newProductsGrid) {
                currentProductsGrid.innerHTML = newProductsGrid.innerHTML;
            }else{
                redirect(`${url.pathname}?${searchParams.toString()}`);
            }

            const newPager = tempDiv.querySelector('.products_pager');
            const currentPager = document.querySelector('.products_pager');
            if (currentPager && newPager) {
                currentPager.innerHTML = newPager.innerHTML;
            }
            const offcanvas = document.querySelector('.o_website_offcanvas');
            const newOffcanvas = tempDiv.querySelector('.o_website_offcanvas');
            if (offcanvas && newOffcanvas) {
                const shopPageEl = document.querySelector('.o_wsale_products_page');
                this.services['public.interactions'].stopInteractions(shopPageEl);
                offcanvas.innerHTML = newOffcanvas.innerHTML;
                this.services['public.interactions'].startInteractions(shopPageEl);
            }
            const applyBtn = document.querySelector('#o_wsale_apply_filters_btn');
            if (applyBtn) {
                applyBtn.innerHTML = `Apply Filters <span class="badge rounded-pill bg-o-color-3 text-o-color-1 ms-2">${data.count}</span>`;
            }
            window.history.pushState({}, '', `${url.pathname}?${searchParams.toString()}`);
            if (productGridWrapper) productGridWrapper.classList.remove('opacity-50');
        }else {
            redirect(`${url.pathname}?${searchParams.toString()}`);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.price_range', PriceRange);
