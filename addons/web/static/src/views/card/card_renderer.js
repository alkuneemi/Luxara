import { ColorList } from "@web/core/colorlist/colorlist";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Field } from "@web/views/fields/field";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewCompiler } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";
import { getFormattedValue } from "../utils";
import { CARD_ATTRIBUTE, MENU_ATTRIBUTE } from "./card_arch_parser";
import { CardCompiler } from "./card_compiler";

import { Component, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { CardDropdownMenuWrapper } from "./card_dropdown_menu_wrapper";
import { CardCoverImageDialog } from "./card_cover_image_dialog";
// import { useViewButtons } from "../view_button/view_button_hook";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

const { COLORS } = ColorList;

const formatters = registry.category("formatters");

/**
 * Returns the index of a color determined by a given record.
 */
export function getColorIndex(value) {
    if (typeof value === "number") {
        return Math.round(value) % COLORS.length;
    } else if (typeof value === "string") {
        const charCodeSum = [...value].reduce((acc, _, i) => acc + value.charCodeAt(i), 0);
        return charCodeSum % COLORS.length;
    } else {
        return 0;
    }
}

/**
 * Returns a "raw" version of the field value on a given record.
 *
 * @param {Record} record
 * @param {string} fieldName
 * @returns {any}
 */
export function getRawValue(record, fieldName) {
    const field = record.fields[fieldName];
    const value = record.data[fieldName];
    switch (field.type) {
        case "one2many":
        case "many2many": {
            return value.count ? value.currentIds : [];
        }
        case "many2one": {
            return (value && value.id) || false;
        }
        case "date":
        case "datetime": {
            return value && value.toISO();
        }
        default: {
            return value;
        }
    }
}

/**
 * Returns a formatted version of the field value on a given record.
 *
 * @param {Record} record
 * @param {string} fieldName
 * @returns {string}
 */
function getValue(record, fieldName) {
    const field = record.fields[fieldName];
    const value = record.data[fieldName];
    const formatter = formatters.get(field.type, String);
    return formatter(value, { field, data: record.data });
}

export function getFormattedRecord(record) {
    const formattedRecord = {
        id: {
            value: record.resId,
            raw_value: record.resId,
        },
    };

    for (const fieldName of record.fieldNames) {
        formattedRecord[fieldName] = {
            value: getValue(record, fieldName),
            raw_value: getRawValue(record, fieldName),
        };
    }
    return formattedRecord;
}

export class CardRenderer extends Component {
    static components = {
        Dropdown,
        DropdownItem,
        Field,
        ViewButton,
        Widget,
        CardDropdownMenuWrapper,
        CardCoverImageDialog,
    };
    static defaultProps = {
        colors: COLORS,
        deleteRecord: () => {},
        archiveRecord: () => {},
        openRecord: () => {},
    };
    static props = [
        "archInfo",
        "colors?",
        "Compiler?",
        "deleteRecord?",
        "archiveRecord?",
        "openRecord?",
        "readonly?",
        "record",
    ];
    static CARD_ATTRIBUTE = CARD_ATTRIBUTE;
    static MENU_ATTRIBUTE = MENU_ATTRIBUTE;
    static template = "web.CardRenderer";
    static menuTemplate = "web.CardMenu";
    static Compiler = CardCompiler;
    static CoverImageDialog = CardCoverImageDialog;
    static PROGRESS_COLOR_PREFIX = "o_card_color_";
    static HIGHLIGHT_COLOR_PREFIX = "o_card_color_";

    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.offlineService = useService("offline");

        const { Compiler, archInfo } = this.props;
        const ViewCompiler = Compiler || this.constructor.Compiler;
        const { templateDocs: templates } = archInfo;

        this.templates = useViewCompiler(ViewCompiler, templates);
        this.showMenu = this.constructor.MENU_ATTRIBUTE in templates;

        this.dataState = useState({ record: {}, widget: {} });
        this.createWidget(this.props);
        onWillUpdateProps(this.createWidget);
        useRecordObserver((record) =>
            Object.assign(this.dataState.record, getFormattedRecord(record))
        );
        this.rootRef = useRef("root");

        // TODO AAB: breaks one2many field with virtual ids with kanban button
        // useViewButtons(this.rootRef, {
        //     reload: () => this.props.record.model.load(),
        // });
    }

    get record() {
        return this.dataState.record;
    }

    getFormattedValue(fieldId) {
        const { archInfo, record } = this.props;
        const { name } = archInfo.fieldNodes[fieldId];
        return getFormattedValue(record, name, archInfo.fieldNodes[fieldId]);
    }

    /**
     * Assigns "widget" properties on the card record.
     *
     * @param {Object} props
     */
    createWidget(props) {
        this.dataState.widget = {
            deletable: props.archInfo.activeActions.delete && !props.readonly,
            editable: props.archInfo.activeActions.edit && !props.readonly,
        };
    }

    // TODO AAB: rename into getCardClasses
    getRecordClasses() {
        const { archInfo } = this.props;
        const classes = ["o_card_record d-flex"];
        classes.push(archInfo.cardClassName);
        return classes.join(" ");
    }

    /**
     * @param {Object} params
     */
    triggerAction(params) {
        const { archInfo, deleteRecord, openRecord, record } = this.props;
        const { type } = params;
        switch (type) {
            case "open": {
                return openRecord(record);
            }
            case "archive": {
                return this.archiveRecord(record, true);
            }
            case "unarchive": {
                return this.archiveRecord(record, false);
            }
            case "delete": {
                return deleteRecord(record);
            }
            case "set_cover": {
                const { autoOpen, fieldName } = params;
                const widgets = Object.values(archInfo.fieldNodes)
                    .filter((x) => x.name === fieldName)
                    .map((x) => x.widget);
                const field = record.fields[fieldName];
                if (
                    field.type === "many2one" &&
                    field.relation === "ir.attachment" &&
                    widgets.includes("attachment_image")
                ) {
                    this.dialog.add(this.constructor.CoverImageDialog, {
                        autoOpen,
                        fieldName,
                        record,
                    });
                } else {
                    const warning = _t(
                        `Could not set the cover image: incorrect field ("%s") is provided in the view.`,
                        fieldName
                    );
                    this.notification.add({ title: warning, type: "danger" });
                }
                break;
            }
            default: {
                return this.notification.add(_t("Card: no action for type: %(type)s", { type }), {
                    type: "danger",
                });
            }
        }
    }

    /**
     * Returns the card template's rendering context.
     *
     * Note: the keys answer to outdated standards but should not be altered for
     * the sake of compatibility.
     *
     * @returns {Object}
     */
    get renderingContext() {
        const renderingContext = {
            context: this.props.record.context,
            JSON,
            luxon,
            record: this.dataState.record,
            selection_mode: false,
            widget: this.dataState.widget,
            __comp__: Object.assign(Object.create(this), { this: this }),
        };
        return renderingContext;
    }

    async archiveRecord(record, active) {
        if (active) {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Are you sure that you want to archive this record?"),
                confirmLabel: _t("Archive"),
                confirm: () => record.archive(),
                cancel: () => {},
            });
        } else {
            return record.unarchive();
        }
    }
}
