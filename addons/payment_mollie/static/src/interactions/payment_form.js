import { patch } from '@web/core/utils/patch';
import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {

    async willStart() {
        await super.willStart(...arguments);
        this._updateWalletsVisibility();
    }
});
