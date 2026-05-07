import {
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { ReadonlyEmbeddedDateComponent } from "../../core/date/readonly_date";
import { TimePicker } from "@web/core/time_picker/time_picker";
import { usePopover } from "@web/core/popover/popover_hook";
import { useRef } from "@web/owl2/utils";
const { DateTime } = luxon;

export class EmbeddedDateComponent extends ReadonlyEmbeddedDateComponent {
    static template = "html_editor.EmbeddedDate";

    setup() {
        super.setup();
        this.state = useEmbeddedState(this.props.host);
        this.ref = useRef("embedded-date");

        if (this.props.type === "time") {
            this.picker = usePopover(TimePicker);
            const openPicker = this.picker.open.bind(this.picker);
            this.picker.open = () => {
                const time = DateTime.fromISO(this.state.date, { zone: "utc" })
                    .setZone(this.timeZone)
                    .toFormat("HH:mm");
                openPicker(this.ref.el, {
                    value: time,
                    onChange: ({ hour, minute }) => {
                        this.state.date = DateTime.fromISO(this.state.date, { zone: "utc" })
                            .setZone(this.timeZone)
                            .set({ hour, minute })
                            .toUTC()
                            .toISO();
                        this.picker.close();
                    },
                });
            };
        } else {
            const pickerProps = () => ({
                type: this.props.type,
                value: DateTime.fromISO(this.state.date, { zone: "utc" }).setZone(this.timeZone),
            });
            this.picker = useDateTimePicker({
                target: "embedded-date",
                onChange: (date) => {
                    this.state.date = date.toUTC().toISO();
                },
                showResetButton: false,
                get pickerProps() {
                    return pickerProps();
                },
            });
        }
    }

    get formattedDate() {
        const date = DateTime.fromISO(this.state.date, { zone: "utc" }).setZone(this.timeZone);
        return date.toLocaleString(this.DATE_FORMATS[this.props.type]);
    }

    onClick() {
        this.picker.open();
    }
}

export const dateEmbedding = {
    name: "date",
    Component: EmbeddedDateComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) => new StateChangeManager(config),
};
