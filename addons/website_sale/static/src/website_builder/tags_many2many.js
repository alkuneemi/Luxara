import { ModelMany2Many } from "@html_builder/core/building_blocks/model_many2many";

export class TagsMany2Many extends ModelMany2Many {
    static props = {
        ...ModelMany2Many.props,
        apply: { type: Function, optional: true },
    };

    setSelection(newSelection) {
        super.setSelection(newSelection);
        if (this.props.apply) {
            this.props.apply(newSelection);
        }
    }
    async create(name) {
        const [tagId] = await this.env.services.orm.create(this.state.searchModel, [{
            name: name,
        }]);

        this.setSelection([
            ...this.domState.selection,
            {
                id: tagId,
                name: name,
                display_name: name,
                model: this.state.searchModel,
            },
        ]);
    }
}
