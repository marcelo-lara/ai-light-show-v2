import { cancelPrompt, sendPrompt } from "../llm_intents.ts";
import { getLlmState } from "../llm_state.ts";

export function PromptInput(): HTMLElement {
	const row = document.createElement("div");
	row.className = "prompt-row";

	const input = document.createElement("textarea");
	input.className = "prompt-input";
	input.rows = 3;
	input.placeholder = "Ask the assistant…";

	const actions = document.createElement("div");
	actions.className = "prompt-actions";

	const send = document.createElement("button");
	send.type = "button";
	send.textContent = "Send";
	send.className = "btn primary";

	const cancel = document.createElement("button");
	cancel.type = "button";
	cancel.textContent = "Cancel";
	cancel.className = "btn";

	send.addEventListener("click", () => {
		sendPrompt(input.value);
		if (getLlmState().status === "streaming") input.value = "";
	});

	cancel.addEventListener("click", () => cancelPrompt());

	input.addEventListener("keydown", (ev) => {
		if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) {
			ev.preventDefault();
			send.click();
		}
	});

	actions.append(send, cancel);
	row.append(input, actions);
	return row;
}
