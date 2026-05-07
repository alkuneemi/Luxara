import { patch } from "@web/core/utils/patch";
import { TraceabilityReport } from "@stock/client_actions/stock_traceability_report_backend";

const EXPIRATION_DATE_COLUMN_INDEX = 4;

function hasVisibleExpirationDate(lines) {
    return lines.some(
        (line) =>
            line.columns[EXPIRATION_DATE_COLUMN_INDEX] ||
            (!line.isFolded && hasVisibleExpirationDate(line.lines))
    );
}

patch(TraceabilityReport.prototype, {
    async onWillStart() {
        await super.onWillStart();
        this.updateExpirationDateColumn();
    },

    get hasExpirationDate() {
        return this._hasExpirationDate;
    },

    async toggleLine(line) {
        await super.toggleLine(line);
        this.updateExpirationDateColumn();
    },

    updateExpirationDateColumn() {
        this._hasExpirationDate = hasVisibleExpirationDate(this.state.lines);
    },
});
