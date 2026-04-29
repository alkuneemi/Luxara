import { Component } from "@odoo/owl";
import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";

export class EmbeddedWhiteboardComponent extends Component {
    static template = "html_editor.EmbeddedWhiteboard";
    static props = {
        host: Object,
        url: { type: String },
        type: { type: String },
        previewUrl: { type: String, optional: true },
        embedUrl: { type: String, optional: true },
        error: { type: Boolean, optional: true },
    };
}

export const whiteboardEmbedding = {
    name: "whiteboard",
    Component: EmbeddedWhiteboardComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
};
