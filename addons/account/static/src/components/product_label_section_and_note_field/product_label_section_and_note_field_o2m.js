import {
    SectionAndNoteFieldOne2Many,
    sectionAndNoteFieldOne2Many,
    SectionAndNoteListRenderer,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { registry } from "@web/core/registry";

export class ProductLabelSectionAndNoteListRender extends SectionAndNoteListRenderer {
    setup() {
        super.setup();
        this.descriptionColumn = "name";
        this.productColumns = ["product_id"];
        this.conditionalColumns = ["product_id", "quantity", "product_uom_id"];
    }

    processAllColumn(allColumns, list) {
        allColumns = allColumns.map((column) => {
            if (column["optional"] === "conditional" && this.conditionalColumns.includes(column["name"])) {
                /**
                 * The preference should be different whether:
                 *     - It's a Vendor Bill or an Invoice
                 *     - Sale module is installed
                 * Vendor Bills -> Product should be hidden by default (except when self billing)
                 * Invoices -> conditionalColumns should be hidden by default if Sale module is not installed
                 */
                const isBill = ["in_invoice", "in_refund", "in_receipt"].includes(this.props.list.evalContext.parent.move_type);
                const isInvoice = ["out_invoice", "out_refund", "out_receipt"].includes(this.props.list.evalContext.parent.move_type);
                const isSelfBilling = this.props.list.evalContext.parent.is_self_billing;
                const isSaleInstalled = this.props.list.evalContext.parent.is_sale_installed;
                column["optional"] = "show";
                if (isBill && column["name"] === "product_id" && !isSelfBilling) {
                    column["optional"] = "hide";
                } else if (isInvoice && !isSaleInstalled) {
                    column["optional"] = "hide";
                }
            }
            return column;
        });
        return super.processAllColumn(allColumns, list);
    }

    isCellReadonly(column, record) {
        if (![...this.productColumns, "name"].includes(column.name)) {
            return super.isCellReadonly(column, record);
        }
        // The isCellReadonly method from the ListRenderer is used to determine the classes to apply to the cell.
        // We need this override to make sure some readonly classes are not applied to the cell if it is still editable.
        const isReadonly = super.isCellReadonly(column, record);
        return (
            isReadonly
            && (["cancel", "posted"].includes(record.evalContext.parent.state)
            || record.evalContext.parent.locked)
        )
    }

    getCellTitle(column, record) {
        // When using this list renderer, we don't want the product_id cell to have a tooltip with its label.
        if (this.productColumns.includes(column.name)) {
            return;
        }
        return super.getCellTitle(column, record);
    }

    getActiveColumns() {
        let activeColumns = super.getActiveColumns();
        const productCol = activeColumns.find((col) => this.productColumns.includes(col.name));
        const labelCol = activeColumns.find((col) => col.name === this.descriptionColumn);

        if (productCol && labelCol) {
            activeColumns = activeColumns.filter((col) => !this.productColumns.includes(col.name));
            this.titleField = this.descriptionColumn;
        } else if (productCol) {
            this.titleField = productCol.name;
        }

        return activeColumns;
    }
}

export class ProductLabelSectionAndNoteOne2Many extends SectionAndNoteFieldOne2Many {
    static components = {
        ...super.components,
        ListRenderer: ProductLabelSectionAndNoteListRender,
    };
}

export const productLabelSectionAndNoteOne2Many = {
    ...sectionAndNoteFieldOne2Many,
    component: ProductLabelSectionAndNoteOne2Many,
};

registry
    .category("fields")
    .add("product_label_section_and_note_field_o2m", productLabelSectionAndNoteOne2Many);
