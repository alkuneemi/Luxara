import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";

export class CardDropdownMenuWrapper extends Component {
    static template = "web.CardDropdownMenuWrapper";
    static props = {
        slots: Object,
    };

    setup() {
        this.dropdownControl = useDropdownCloser();
        this.rootRef = useRef("rootRef");
        useLayoutEffect(() => {
            const dropdownEls = this.rootRef.el.querySelectorAll(".dropdown-item");
            dropdownEls.forEach((el) => el.classList.add("o-navigable"));
        });
    }

    onClick(ev) {
        this.dropdownControl.closeAll();
    }
}
