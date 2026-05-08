import { Component, onMounted } from "@odoo/owl";
import { PriceFormatter } from "../price_formatter/price_formatter";
import { useRef } from "@web/owl2/utils";

export class FeedbackPaymentSummary extends Component {
    static template = "point_of_sale.FeedbackPaymentSummary";
    static components = { PriceFormatter };
    static props = {
        formattedAmount: { type: String },
        class: { type: String, optional: true },
    };

    setup() {
        this.summaryContainerRef = useRef("feedback-summary");
        this.amountTextRef = useRef("amount");

        onMounted(() => {
            this.scaleAmountText();
        });
    }

    scaleAmountText() {
        const containerWidth = this.summaryContainerRef.el.offsetWidth * 0.8; // 80% of the container width to have some space on the sides
        const textWidth = this.amountTextRef.el.scrollWidth;

        const scale = Math.min(1, containerWidth / textWidth);
        this.amountTextRef.el.style.transform = `scale(${scale})`;
    }
}
