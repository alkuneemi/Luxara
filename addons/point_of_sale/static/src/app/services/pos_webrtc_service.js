import { registry } from "@web/core/registry";
import { logPosMessage } from "../utils/pretty_console_log";
import { getOnNotified, uuidv4 } from "@point_of_sale/utils";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

export const CONSOLE_COLOR = "#F5B427";

/**
 * WebRTC-based service to enable direct peer-to-peer communication between
 * multiple PoS entities (e.g. POS terminals, customer displays, etc).
 *
 * This service replaces the traditional server-mediated communication flow
 * (RPC → server → bus notification) with a more efficient peer-to-peer channel
 * when no server-side processing or persistence is required.
 *
 * Instead of routing messages through the backend, peers establish a direct
 * WebRTC data channel and exchange messages in real time, reducing latency
 * and server load.
 *
 * ---------------------------------------------------------------------------
 * How it works
 * ---------------------------------------------------------------------------
 *
 * 1. Signaling phase (via server/bus):
 *
 *        ┌───────────────┐                           ┌───────────────┐
 *        │    Peer A     │                           │    Peer B     │
 *        └──────┬────────┘                           └──────┬────────┘
 *               │                                           │
 *               │   ready                                   │
 *               ├───────────────RPC/Bus─────────────────────▶
 *               │                                           │
 *               │                               ready       │
 *               ◀──────────────RPC/Bus──────────────────────┤
 *               │                                           │
 *               │   offer (SDP)                             │
 *               ├───────────────RPC/Bus─────────────────────▶
 *               │                                           │
 *               │                               answer (SDP)│
 *               ◀──────────────RPC/Bus──────────────────────┤
 *               │                                           │
 *               │   ICE candidates exchange (multiple)      │
 *               ◀──────────────RPC/Bus──────────────────────▶
 *               │                                           │
 *
 *    - Peers discover each other using "ready" messages.
 *    - One peer initiates the connection by sending an "offer".
 *    - The other peer responds with an "answer".
 *    - ICE candidates are exchanged to establish the best network path.
 *    - All signaling messages are routed via RPC + bus (server acts only as relay).
 *
 * 2. Connection establishment:
 *    - RTCPeerConnection is created and negotiation is completed.
 *
 * 3. Data channel communication:
 *    - A WebRTC DataChannel is opened after successful negotiation.
 *    - Messages are exchanged directly between peers (P2P).
 *
 * ---------------------------------------------------------------------------
 * Typical Use Cases
 * ---------------------------------------------------------------------------
 * - Updating customer display in real time
 * - Broadcasting lightweight events without server involvement
 *
 * ---------------------------------------------------------------------------
 * Notes
 * ---------------------------------------------------------------------------
 * - The server is only used for signaling, not for actual data transfer.
 * - STUN and TURN servers are used to establish connectivity across networks.
 * - This service assumes all peers are within the same POS configuration scope.
 */

const RTC_CONFIG = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" },
        { urls: "stun:stun1.l.google.com:19302" },
        { urls: "stun:stun2.l.google.com:19302" },
        {
            urls: "turn:global.relay.metered.ca:443",
            username: "2d14bd753b2397aff3867c94",
            credential: "sSfRBJ1Q5IE9zH1z",
        },
        {
            urls: "turns:global.relay.metered.ca:443?transport=tcp",
            username: "2d14bd753b2397aff3867c94",
            credential: "sSfRBJ1Q5IE9zH1z",
        },
    ],
    iceCandidatePoolSize: 8,
};

const CONNECTION_TIMEOUT_MS = 15000;

export class PosWebrtcService {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { bus_service }) {
        this.env = env;
        this.bus = bus_service;

        this.accessToken = session.access_token || odoo.access_token;
        this.configId = session.config_id || odoo.pos_config_id;

        this.peerId = uuidv4();
        this.knownPeers = new Set();
        this.peers = new Map();
        this.pendingCandidates = new Map();

        this.listeners = new Set(); // callback listeners to handle received data from Peers
        this.shouldInitiateOffer = false;
    }

    async init(identifier = 0) {
        this.signaling = {
            postMessage: this.sendSignal.bind(this),
            onmessage: this.handleSignalingMessage.bind(this),
            identifier,
        };
        getOnNotified(this.bus, this.accessToken)(
            this.channelName,
            this.signaling.onmessage.bind(this)
        );
        await this.signaling.postMessage({ type: "ready", fromPeerId: this.peerId });
    }

    handleSignalingMessage(payload) {
        const { type, fromPeerId, toPeerId } = payload;
        if ((fromPeerId && fromPeerId === this.peerId) || (toPeerId && toPeerId !== this.peerId)) {
            return;
        }
        switch (type) {
            case "ready":
                this.handleReady(payload);
                break;
            case "candidate":
                this.handleCandidate(payload);
                break;
            case "offer":
                this.handleOffer(payload);
                break;
            case "answer":
                this.handleAnswer(payload);
                break;
            default:
                logPosMessage(
                    "PosWebrtcService",
                    "Signaling",
                    "Unhandled msg type",
                    CONSOLE_COLOR,
                    [payload]
                );
                break;
        }
    }

    async sendSignal(payload) {
        try {
            await rpc("/pos_webrtc_signaling/", {
                pos_config_id: this.configId,
                payload,
                identifier: this.signaling.identifier,
            });
        } catch (error) {
            logPosMessage(
                "PosWebrtcService",
                "sendSignal",
                "Failed to send signaling message",
                CONSOLE_COLOR,
                [error]
            );
        }
    }

    send(data) {
        const payload = typeof data === "string" ? data : JSON.stringify(data);

        let sent = false;
        for (const peer of this.peers.values()) {
            if (peer.channel?.readyState === "open") {
                try {
                    peer.channel.send(payload);
                } catch {
                    this.removePeer(peer.peerId);
                    continue;
                }
                sent = true;
            }
        }

        if (!sent) {
            logPosMessage(
                "PosWebrtcService",
                "send",
                "No open data channels available",
                CONSOLE_COLOR
            );
        }
    }

    async establishConnection(targetPeerId) {
        if (!targetPeerId) {
            for (const peerId of this.knownPeers) {
                if (this.shouldInitiate(peerId) && !this.peers.has(peerId)) {
                    this.establishConnection(peerId);
                }
            }
            return;
        }
        const peer = this.createPeer(targetPeerId);
        if (!peer) {
            return;
        }

        peer.createDataChannel("notifications");

        try {
            const offer = await peer.peerConnection.createOffer();
            await peer.peerConnection.setLocalDescription(offer);
            await this.signaling.postMessage({
                type: "offer",
                fromPeerId: this.peerId,
                toPeerId: targetPeerId,
                sdp: offer.sdp,
            });
        } catch (error) {
            logPosMessage(
                "PosWebrtcService",
                "establishConnection",
                `Failed to create offer for ${targetPeerId}`,
                CONSOLE_COLOR,
                [error]
            );
            this.removePeer(targetPeerId);
        }
    }

    get channelName() {
        return `POS_WEBRTC_SIGNALING-${this.signaling.identifier}`;
    }

    addListener(callback) {
        this.listeners.add(callback);
    }

    removeListener(callback) {
        this.listeners.delete(callback);
    }

    async handleCandidate(candidate) {
        const peerId = candidate.fromPeerId;
        const peer = this.peers.get(peerId);
        if (!peer) {
            this.bufferCandidate(peerId, candidate);

            logPosMessage(
                "PosWebrtcService",
                "handleCandidate",
                "no peer connection for candidate",
                CONSOLE_COLOR
            );
            return;
        }
        if (!peer.peerConnection.remoteDescription) {
            this.bufferCandidate(peerId, candidate);
            return;
        }
        await this.addIceCandidate(peer.peerConnection, candidate);
    }

    async handleReady(data) {
        const peerId = data.fromPeerId;
        if ((!peerId && this.peers.size) || this.peers.has(peerId)) {
            return;
        }
        this.knownPeers.add(peerId);
        if (this.shouldInitiateOffer) {
            this.establishConnection(peerId);
        } else {
            await this.signaling.postMessage({ type: "ready", fromPeerId: this.peerId });
        }
    }

    async handleOffer(offer) {
        const peerId = offer.fromPeerId;
        if (this.peers.has(peerId)) {
            logPosMessage(
                "PosWebrtcService",
                "handleOffer",
                `existing peerconnection for ${peerId}`,
                CONSOLE_COLOR
            );
            return;
        }
        const peer = this.createPeer(peerId);
        if (!peer) {
            return;
        }
        peer.peerConnection.ondatachannel = (event) => this.onDataChannelReceived(peerId, event);

        try {
            await peer.peerConnection.setRemoteDescription(offer);
            await this.flushBufferedCandidates(peerId);

            const answer = await peer.peerConnection.createAnswer();
            await peer.peerConnection.setLocalDescription(answer);
            await this.signaling.postMessage({
                type: "answer",
                fromPeerId: this.peerId,
                toPeerId: peerId,
                sdp: answer.sdp,
            });
        } catch (error) {
            logPosMessage(
                "PosWebrtcService",
                "handleOffer",
                `Failed to handle offer from ${peerId}`,
                CONSOLE_COLOR,
                [error]
            );
            this.removePeer(peerId);
        }
    }

    async handleAnswer(answer) {
        const peerId = answer.fromPeerId;
        const peer = this.peers.get(peerId);
        if (!peer) {
            logPosMessage(
                "PosWebrtcService",
                "handleAnswer",
                `no peerconnection for answer ${peerId}`,
                CONSOLE_COLOR
            );
            return;
        }
        try {
            await peer.peerConnection.setRemoteDescription(answer);
            await this.flushBufferedCandidates(peerId);
        } catch (error) {
            logPosMessage(
                "PosWebrtcService",
                "handleAnswer",
                `Failed to apply answer from ${peerId}`,
                CONSOLE_COLOR,
                [error]
            );
            this.removePeer(peerId);
        }
    }

    onDataChannelReceived(peerId, event) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }
        peer.setChannel(event.channel, "receive");
    }

    shouldInitiate(otherPeerId) {
        return String(this.peerId).localeCompare(String(otherPeerId)) === 1;
    }

    bufferCandidate(peerId, candidate) {
        if (!this.pendingCandidates.has(peerId)) {
            this.pendingCandidates.set(peerId, []);
        }
        this.pendingCandidates.get(peerId).push(candidate);
    }

    async flushBufferedCandidates(peerId) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }
        const buffered = this.pendingCandidates.get(peerId);
        if (!buffered || !buffered.length) {
            return;
        }
        for (const candidate of buffered) {
            await this.addIceCandidate(peer.peerConnection, candidate);
        }
        this.pendingCandidates.delete(peerId);
    }

    async addIceCandidate(peerConnection, candidate) {
        const iceCandidate = candidate.candidate ? candidate : null;
        try {
            await peerConnection.addIceCandidate(iceCandidate);
        } catch (error) {
            logPosMessage(
                "PosWebrtcService",
                "addIceCandidate",
                "Failed to add ICE candidate",
                CONSOLE_COLOR,
                [error]
            );
        }
    }

    createPeer(peerId) {
        if (this.peers.has(peerId)) {
            return;
        }
        const peer = new Peer({
            peerId,
            localPeerId: this.peerId,
            onSignal: (message) => this.signaling.postMessage(message),
            onRemove: (id) => this.removePeer(id),
            onMessage: (data) => this._onChannelMessageCallback(data),
        });
        this.peers.set(peerId, peer);
        peer.startTimeout();
        return peer;
    }

    _onChannelMessageCallback(data) {
        for (const listener of this.listeners) {
            listener(data);
        }
    }

    removePeer(peerId) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }
        peer.close();
        this.peers.delete(peerId);
        this.pendingCandidates.delete(peerId);
    }
}

class Peer {
    constructor({ peerId, localPeerId, onSignal, onRemove, onMessage }) {
        this.peerId = peerId;
        this.localPeerId = localPeerId;
        this.onSignal = onSignal;
        this.onRemove = onRemove;
        this.onMessage = onMessage;

        this.peerConnection = new RTCPeerConnection(RTC_CONFIG);
        this.channel = null;
        this.isClosing = false;
        this.connectionTimer = null;

        this.peerConnection.onicecandidate = (e) => this._onIceCandidate(e);
        this.peerConnection.onconnectionstatechange = () => this._onConnectionStateChange();
        this.peerConnection.oniceconnectionstatechange = () => this._onIceConnectionStateChange();
    }

    closePeer() {
        this.clearTimeout();
        this.onRemove(this.peerId);
    }

    startTimeout() {
        this.clearTimeout();
        this.connectionTimer = setTimeout(() => {
            // cleaning up peers that never connect
            if (!this.isConnected()) {
                this.onRemove(this.peerId);
            }
        }, CONNECTION_TIMEOUT_MS);
    }

    clearTimeout() {
        if (this.connectionTimer) {
            clearTimeout(this.connectionTimer);
        }
        this.connectionTimer = null;
    }

    isConnected() {
        return (
            this.channel?.readyState === "open" &&
            this.peerConnection?.connectionState === "connected"
        );
    }

    close() {
        this.isClosing = true;
        if (this.channel) {
            this.channel.close();
        }
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        this.clearTimeout();
    }

    createDataChannel(name) {
        const channel = this.peerConnection.createDataChannel(name);
        this.setChannel(channel, "send");
        return channel;
    }

    setChannel(channel, direction) {
        this.channel = channel;
        this._attachChannelHandlers(direction);
    }

    _attachChannelHandlers(direction) {
        this.channel.onopen = () => this._onChannelStateChange(direction);
        this.channel.onclose = () => this._onChannelStateChange(direction);
        this.channel.onmessage = (event) => this.onMessage(event.data);
        this.channel.onerror = (event) => this._onChannelError(event);
    }

    _onChannelStateChange(direction) {
        if (this.isClosing) {
            return;
        }
        const readyState = this.channel.readyState;
        this.clearTimeout();
        if (readyState !== "open") {
            this.closePeer();
        }

        logPosMessage(
            "PosWebrtcService",
            "ChannelState",
            `Channel ${direction} ${readyState} for peer ${this.peerId}`,
            CONSOLE_COLOR
        );
    }

    _onChannelError(event) {
        this.closePeer();
        logPosMessage(
            "PosWebrtcService",
            "ChannelError",
            `Channel error for peer ${this.peerId}`,
            CONSOLE_COLOR,
            [event]
        );
    }

    _onIceCandidate(e) {
        const message = {
            type: "candidate",
            fromPeerId: this.localPeerId,
            toPeerId: this.peerId,
            candidate: null,
        };
        if (e.candidate) {
            message.candidate = e.candidate.candidate;
            message.sdpMid = e.candidate.sdpMid;
            message.sdpMLineIndex = e.candidate.sdpMLineIndex;
        }
        this.onSignal(message);
    }

    _onConnectionStateChange() {
        if (this.isClosing) {
            return;
        }
        const state = this.peerConnection.connectionState;
        if (state === "connected") {
            this.clearTimeout();
            return;
        }
        if (["closed", "failed", "disconnected"].includes(state)) {
            this.closePeer();
        }
    }

    _onIceConnectionStateChange() {
        if (this.isClosing) {
            return;
        }
        const state = this.peerConnection.iceConnectionState;
        if (["failed", "disconnected"].includes(state)) {
            this.closePeer();
        }
    }
}

export const posWebrtcService = {
    dependencies: ["bus_service"],
    async start(env, services) {
        const service = new PosWebrtcService(env, services);
        return service;
    },
};

registry.category("services").add("pos_webrtc", posWebrtcService);
