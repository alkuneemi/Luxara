import { registerComposerAction } from "@mail/core/common/composer_actions";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class VoiceRecorder extends Component {
    static props = ["composer", "state"];
    static template = "mail.VoiceRecorder";
    get title() {
        return _t("Stop Recording");
    }
    get cancelTitle() {
        return _t("Cancel");
    }
}

registerComposerAction("voice-start", {
    condition: ({ composer, owner }) =>
        composer.targetThread?.channel &&
        owner.voiceRecorder &&
        !owner.voiceRecorder?.recording &&
        !composer.voiceAttachment,
    icon: "fa fa-microphone",
    name: _t("Voice Message"),
    onSelected: ({ owner }) => owner.voiceRecorder.onClick(),
    sequence: 10,
});
registerComposerAction("voice-recording", {
    component: VoiceRecorder,
    componentProps: ({ composer, owner }) => ({ composer, state: owner.voiceRecorder }),
    condition: ({ composer, owner }) =>
        composer.targetThread?.channel && owner.voiceRecorder?.recording,
    sequenceQuick: 10,
});
