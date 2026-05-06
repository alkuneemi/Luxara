import { Record } from "@web/model/record";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";

import { CardRenderer } from "./card_renderer";
import { CARD_ATTRIBUTE, MENU_ATTRIBUTE, CardArchParser } from "./card_arch_parser";

import { Component, xml } from "@odoo/owl";

export class Card extends Component {
    static template = xml`
        <div class="o_card">
            <Record t-props="this.recordProps" t-slot-scope="data">
                <CardRenderer record="data.record" t-props="this.rendererProps"/>
            </Record>
        </div>`;
    static components = {
        Record,
        CardRenderer,
    };
    static defaultProps = {};
    static props = [
        "card",
        "resModel",
        "resId",
        "fields",
        "context?",
        "hooks?",
        "openRecord?",
        "readonly?",
    ];
    static CARD_ATTRIBUTE = CARD_ATTRIBUTE;
    static MENU_ATTRIBUTE = MENU_ATTRIBUTE;

    setup() {
        const resModel = this.props.resModel;
        const relatedModels = { [resModel]: { fields: this.props.fields } };
        const archInfo = new CardArchParser().parse(this.props.card, relatedModels, resModel);
        const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, this.props.fields);
        this.archInfo = archInfo;
        this.activeFields = activeFields;
        this.fields = fields;
    }

    get recordProps() {
        return {
            activeFields: this.activeFields,
            fields: this.fields,
            resId: this.props.resId,
            resModel: this.props.resModel,
            context: this.props.context,
            hooks: this.props.hooks,
        };
    }

    get rendererProps() {
        return {
            archInfo: this.archInfo,
            openRecord: this.props.openRecord,
            readonly: this.props.readonly,
        };
    }
}
