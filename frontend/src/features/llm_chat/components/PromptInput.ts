import { cancelPrompt, sendPrompt } from "../llm_intents.ts";
import { getLlmState, isLlmActiveStatus } from "../llm_state.ts";
import { Button } from "../../../shared/components/controls/Button.ts";
import { selectEditLock } from "../../../shared/state/selectors.ts";

export function PromptInput(): HTMLElement {
	const state = getLlmState();
	const isShowLocked = selectEditLock() === true;
	const isLlmActive = isLlmActiveStatus(state.status);

	const row = document.createElement("div");
	row.className = "prompt-row";

	const input = document.createElement("textarea");
	input.className = "prompt-input";
	input.rows = 1;
	input.placeholder = isShowLocked ? "LLM unavailable while show is running." : "Ask the assistant…";
 	input.setAttribute("aria-label", "Message input");
	input.disabled = isShowLocked || isLlmActive;

	const actions = document.createElement("div");
	actions.className = "prompt-actions";

	const send = Button({
		caption: "↑",
		state: "primary",
		bindings: {
			title: "Send prompt",
			disabled: isShowLocked || isLlmActive,
		},
	});

	const stop = Button({
		caption: "Stop",
		state: "default",
		bindings: {
			title: "Stop generating",
			disabled: isShowLocked || !isLlmActive,
		},
	});

	const updateSendState = () => {
		send.disabled = isShowLocked || isLlmActive || input.value.trim().length === 0;
	};

	const syncComposerHeight = () => {
		input.style.height = "0px";
		const nextHeight = Math.min(input.scrollHeight, 140);
		input.style.height = `${nextHeight}px`;
	};

	const submitPrompt = () => {
		if (isShowLocked || isLlmActive || input.value.trim().length === 0) return;
		sendPrompt(input.value);
		if (isLlmActiveStatus(getLlmState().status)) {
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
		if (isShowLocked || isLlmActive) return;
		if (ev.key === "Enter" && !ev.shiftKey && !ev.altKey && !ev.ctrlKey && !ev.metaKey && !ev.isComposing) {
			ev.preventDefault();
			submitPrompt();
		}
	});

	syncComposerHeight();
	updateSendState();
	if (isLlmActive) actions.append(stop);
	actions.append(send);
	row.append(input, actions);
	return row;
}
