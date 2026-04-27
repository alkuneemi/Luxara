import { redirect } from '@web/core/utils/urls';

export async function updateShopContent({
    url,
    searchParams,
    services,
    options = {}
}) {
    const {
        updateOffcanvas = true,
        updateHistory = true,
    } = options;

    const productGridWrapper = document.querySelector('.o_wsale_products_grid_table_wrapper');
    productGridWrapper?.classList.add('opacity-50');

    try {
        const response = await fetch(`${url.pathname}?${searchParams.toString()}`, {
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });
        const data = await response.json();

        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = data.html;

        const newGrid = tempDiv.querySelector('.o_wsale_products_grid_table');
        const currentGrid = document.querySelector('.o_wsale_products_grid_table');

        if (currentGrid && newGrid) {
            currentGrid.innerHTML = newGrid.innerHTML;
        }else{
            redirect(`${url.pathname}?${searchParams.toString()}`);
        }

        const newPager = tempDiv.querySelector('.products_pager');
        const currentPager = document.querySelector('.products_pager');

        if (currentPager && newPager) {
            currentPager.innerHTML = newPager.innerHTML;
        }

        if (updateOffcanvas) {
            const offcanvas = document.querySelector('.o_website_offcanvas');
            const newOffcanvas = tempDiv.querySelector('.o_website_offcanvas');

            if (offcanvas && newOffcanvas) {
                const shopPageEl = document.querySelector('.o_wsale_products_page');
                services?.['public.interactions']?.stopInteractions(shopPageEl);
                offcanvas.innerHTML = newOffcanvas.innerHTML;
                services?.['public.interactions']?.startInteractions(shopPageEl);
            }
        }

        const applyBtn = document.querySelector('#o_wsale_apply_filters_btn');
        if (applyBtn) {
            applyBtn.innerHTML = `
                Apply Filters
                <span class="badge rounded-pill bg-o-color-3 text-o-color-1 ms-2">
                    ${data.count}
                </span>`;
        }

        if (updateHistory) {
            window.history.pushState({}, '', `${url.pathname}?${searchParams.toString()}`);
        }

        return data;

    } catch (error) {
        console.warn('[shop_ajax] update failed:', error);

        redirect(`${url.pathname}?${searchParams.toString()}`);

    } finally {
        productGridWrapper?.classList.remove('opacity-50');
    }
}
