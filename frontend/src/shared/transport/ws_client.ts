import type { ConnectionState, WsInbound, WsOutbound } from "./protocol.ts";

type Handlers = {
  onConnectionState: (s: ConnectionState) => void;
  onMessage: (m: WsInbound) => void;
};

export class WsClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = "disconnected";
  private retry = 0;

  constructor(
    private url: string,
    private handlers: Handlers,
  ) {}

  get connectionState(): ConnectionState {
    return this.state;
  }

  connect(sendHello?: WsOutbound) {
    if (this.state === "connected" || this.state === "connecting") return;

    this.setState(this.retry > 0 ? "reconnecting" : "connecting");

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.retry = 0;
      this.setState("connected");
      if (sendHello) this.send(sendHello);
    };

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as WsInbound;
        this.handlers.onMessage(msg);
      } catch (e) {
        console.warn("WS parse error:", e);
      }
    };

    this.ws.onclose = () => {
      this.ws = null;
      this.setState("disconnected");
      this.scheduleReconnect(sendHello);
    };

    this.ws.onerror = () => {
      // Let onclose handle reconnect.
    };
  }

  send(msg: WsOutbound) {
    if (!this.ws || this.state !== "connected") return;
    this.ws.send(JSON.stringify(msg));
  }

  close() {
    this.retry = 0;
    this.ws?.close();
    this.ws = null;
    this.setState("disconnected");
  }

  private scheduleReconnect(sendHello?: WsOutbound) {
    this.retry++;
    const delay = Math.min(3000, 300 * Math.pow(2, this.retry - 1));
    setTimeout(() => this.connect(sendHello), delay);
  }

  private setState(s: ConnectionState) {
    this.state = s;
    this.handlers.onConnectionState(s);
  }
}
