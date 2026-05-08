import { useRef } from "@web/owl2/utils";
import { useSelection } from "@mail/utils/common/hooks";

import { Component } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { isEventHandled } from "@web/core/utils/misc";

export class CreatePollOptionDialog extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["model", "onClickRemove", "deletable"];
    static template = "mail.CreatePollOptionDialog";

    setup() {
        this.pickerRef = useRef("picker");
        this.rootRef = useAutofocus({ refName: "root" });
        this.ui = useService("ui");
        useSelection({
            refName: "root",
            model: this.props.model,
            preserveOnClickAwayPredicate: async (ev) => {
                await new Promise(setTimeout);
                return (
                    isEventHandled(ev, "emoji.selectEmoji") ||
                    this.pickerRef.el?.contains(ev.target)
                );
            },
        });
        this.emojiPicker = useEmojiPicker(undefined, {
            onSelect: (emoji) => {
                this.props.model.emoji = emoji;
                if (!this.ui.isSmall) {
                    this.rootRef.el?.focus();
                }
            },
        });
    }

    onClickAddEmoji(ev, action = "toggle") {
        if (action === "dropdown") {
            if (this.emojiPicker.isOpen) {
                ev.stopPropagation();
                this.emojiPicker.close();
            }
            return;
        }
        this.emojiPicker[action](this.ui.isSmall ? undefined : this.pickerRef);
    }

    onClickRemoveEmoji() {
        this.props.model.emoji = "";
    }
}
