/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { SaleDetailsButton } from "@point_of_sale/app/components/navbar/sale_details_button/sale_details_button";
import { DailySalesReportPopup } from "@pos_hr/app/components/popups/daily_sales_report_popup/daily_sales_report_popup";
import { patch } from "@web/core/utils/patch";
import { renderToElement } from "@web/core/utils/render";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

export async function handleSaleDetailsWithEmployees(pos, hardwareProxy, dialog) {
    const payload = await makeAwaitable(dialog, DailySalesReportPopup, {
        title: _t("Session Report"),
    });

    if (!payload) {
        return;
    }

    // Print global report
    const saleDetails = await pos.data.call(
        "report.point_of_sale.report_saledetails",
        "get_sale_details",
        [false, false, false, [pos.session.id]]
    );
    let report = renderToElement(
        "point_of_sale.SaleDetailsReport",
        Object.assign({}, saleDetails, {
            date: new Date().toLocaleString(),
            pos: pos,
            formatCurrency: pos.env.utils.formatCurrency,
        })
    );
    const { successful, message } = await hardwareProxy.printer.printReceipt(report);
    if (!successful) {
        dialog.add(AlertDialog, {
            title: message.title,
            body: message.body,
        });
        return;
    }

    // Print employee reports
    if (payload.add_report_per_employee) {
        const employeeIds = await pos.data.call("pos.session", "get_session_employee_ids", [
            [pos.session.id],
        ]);

        for (const empId of employeeIds) {
            const empSaleDetails = await pos.data.call(
                "report.pos_hr.single_employee_sales_report",
                "get_sale_details",
                [false, false, false, [pos.session.id], empId]
            );
            report = renderToElement(
                "point_of_sale.SaleDetailsReport",
                Object.assign({}, empSaleDetails, {
                    date: new Date().toLocaleString(),
                    pos: pos,
                    formatCurrency: pos.env.utils.formatCurrency,
                })
            );
            const result = await hardwareProxy.printer.printReceipt(report);
            if (!result.successful) {
                dialog.add(AlertDialog, {
                    title: result.message.title,
                    body: result.message.body,
                });
                break;
            }
        }
    }
}

patch(Navbar.prototype, {
    async showSaleDetails() {
        if (this.pos.config.module_pos_hr) {
            await handleSaleDetailsWithEmployees(this.pos, this.hardwareProxy, this.dialog);
        } else {
            super.showSaleDetails();
        }
    },
});

patch(SaleDetailsButton.prototype, {
    async onClick() {
        if (this.pos.config.module_pos_hr) {
            await handleSaleDetailsWithEmployees(this.pos, this.hardwareProxy, this.dialog);
        } else {
            super.onClick();
        }
    },
});
