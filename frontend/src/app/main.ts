import { boot } from "./boot.ts";
import { mountAppShell } from "./AppShell.ts";

const root = document.getElementById("app");
if (!root) throw new Error("Missing #app root");

const bootstrap = (window.__BOOTSTRAP_STATE__ as { wsUrl?: string; backendHttpOrigin?: string } | undefined);
const bootstrapWs = bootstrap?.wsUrl;
const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const wsUrl = bootstrapWs ?? `${protocol}://${window.location.host}/ws`;

boot({ wsUrl, backendHttpOrigin: bootstrap?.backendHttpOrigin });
mountAppShell(root);
