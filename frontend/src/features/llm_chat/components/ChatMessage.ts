import { Button } from "../../../shared/components/controls/Button.ts";
import { confirmAction, rejectAction } from "../llm_intents.ts";
import type { ChatMessage as ChatMessageModel } from "../llm_state.ts";

export function ChatMessage(message: ChatMessageModel): HTMLElement {
	const row = document.createElement("article");
	row.className = `chat-msg ${message.role}`;
	if (message.kind) row.classList.add(`kind-${message.kind}`);

	const text = document.createElement("p");
	text.className = "chat-msg-text";
	text.textContent = message.text;

	row.append(text);

	if (message.action) {
		const title = document.createElement("p");
		title.className = "chat-msg-title";
		title.textContent = message.action.title;
		row.prepend(title);

		const actions = document.createElement("div");
		actions.className = "chat-msg-actions";
		actions.append(
			Button({
				caption: "Confirm",
				state: "primary",
				bindings: {
					title: "Confirm action",
					onClick: () => confirmAction(message.action!.requestId, message.action!.actionId),
				},
			}),
			Button({
				caption: "Reject",
				state: "default",
				bindings: {
					title: "Reject action",
					onClick: () => rejectAction(message.action!.requestId, message.action!.actionId),
				},
			}),
		);
		row.append(actions);
	}

	return row;
}
