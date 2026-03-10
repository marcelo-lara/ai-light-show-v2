import { cancelPrompt, sendPrompt } from "../llm_intents.ts";
import { getLlmState } from "../llm_state.ts";

export function PromptInput(): HTMLElement {
	const state = getLlmState();
	const isStreaming = state.status === "streaming";

	const row = document.createElement("div");
	row.className = "prompt-row";

	const input = document.createElement("textarea");
	input.className = "prompt-input";
	input.rows = 1;
	input.placeholder = "Ask the assistant…";
 	input.setAttribute("aria-label", "Message input");

	const actions = document.createElement("div");
	actions.className = "prompt-actions";

	const send = document.createElement("button");
	send.type = "button";
	send.textContent = "↑";
	send.setAttribute("aria-label", "Send prompt");
	send.title = "Send";
	send.className = "btn primary send-arrow";
	send.disabled = isStreaming;

	const stop = document.createElement("button");
	stop.type = "button";
	stop.textContent = "Stop";
	stop.className = "btn stop-stream";
	stop.title = "Stop generating";

	const updateSendState = () => {
		send.disabled = isStreaming || input.value.trim().length === 0;
	};

	const syncComposerHeight = () => {
		input.style.height = "0px";
		const nextHeight = Math.min(input.scrollHeight, 140);
		input.style.height = `${nextHeight}px`;
	};

	const submitPrompt = () => {
		if (input.value.trim().length === 0) return;
		sendPrompt(input.value);
		if (getLlmState().status === "streaming") {
			input.value = "";
			updateSendState();
		}
	};

	send.addEventListener("click", submitPrompt);
	stop.addEventListener("click", () => cancelPrompt());
	input.addEventListener("input", () => {
		updateSendState();
		syncComposerHeight();
	});

	input.addEventListener("keydown", (ev) => {
		if (isStreaming) return;
		if (ev.key === "Enter" && !ev.shiftKey && !ev.altKey && !ev.ctrlKey && !ev.metaKey && !ev.isComposing) {
			ev.preventDefault();
			submitPrompt();
		}
	});

	syncComposerHeight();
	updateSendState();
	if (isStreaming) actions.append(stop);
	actions.append(send);
	row.append(input, actions);
	return row;
}
