import { Card } from "../../shared/components/layout/Card.ts";
import { selectEditLock } from "../../shared/state/selectors.ts";
import { ChatHistory } from "./components/ChatHistory.ts";
import { PromptInput } from "./components/PromptInput.ts";
import { getLlmState } from "./llm_state.ts";

export function LlmChatView(): HTMLElement {
	const content = document.createElement("div");
	const isDisabled = selectEditLock() === true;
	content.className = `llm-chat${isDisabled ? " is-disabled" : ""}`;

	const state = getLlmState();
	content.append(ChatHistory(state.messages, state.streamingText), PromptInput());

	const card = Card(content, { className: "llm-card" });
	if (isDisabled) {
		card.setAttribute("aria-disabled", "true");
	}
	return card;
}
