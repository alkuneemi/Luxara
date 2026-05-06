import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { Multirange } from '@website/../lib/multirange/multirange_custom';
import { redirect } from '@web/core/utils/urls';

export class RangeFilter extends Interaction {
    static selector = '.o_attr_range[multiple]';

    dynamicContent = {
        _root: {
            't-on-newRangeValue': this.onRangeChange,
        },
    };

    setup() {
        this._values = [];
        const input = this.el;

        try {
            this._values = JSON.parse(input.dataset.values || '[]');
        } catch{
            this._values = [];
        }

        if (!this._values.length) return;

        const values = this._values;

        // Initialize multirange
        const instance = new Multirange(input, {
            displayCounterInput: true,
        });

        // Override to show attribute names instead of numbers
        instance.counterInputUpdate = function() {
            const minIdx = Math.round(this.input.valueLow);
            const maxIdx = Math.round(this.input.valueHigh);
            this.leftCounter.innerText = values[minIdx] ?? "";
            this.rightCounter.innerText = values[maxIdx] ?? "";
            if (this.rangeWithInput) {
                this.leftInput.value = values[minIdx] ?? "";
                this.rightInput.value = values[maxIdx] ?? "";
            }
        };

        instance.update();
        instance.leftInput.disabled = true;
        instance.rightInput.disabled = true;
    }

   onRangeChange(ev) {
    const range = ev.currentTarget;
    const min = Math.round(range.valueLow);
    const max = Math.round(range.valueHigh);
    const attributeId = range.dataset.attributeId;

    const valueIds = JSON.parse(range.dataset.valueIds || '[]');
    const minId = valueIds[min];
    const maxId = valueIds[max];

    const url = new URL(window.location.href);
    const existing = url.searchParams.get('attribute_range') || '';
    const ranges = existing
        ? existing.split(',').filter(r => !r.startsWith(`${attributeId}-`))
        : [];

    if (!(min === 0 && max === Number(range.max))) {
        ranges.push(`${attributeId}-${minId}<${maxId}`);
    }

    if (ranges.length) {
        url.searchParams.set('attribute_range', ranges.join(','));
    } else {
        url.searchParams.delete('attribute_range');
    }

    document.querySelector('.o_wsale_products_grid_table_wrapper')
        ?.classList.add('opacity-50');
    redirect(`${url.pathname}?${url.searchParams.toString()}`);
}
}

registry
    .category('public.interactions')
    .add('website_sale.range_filter', RangeFilter);
