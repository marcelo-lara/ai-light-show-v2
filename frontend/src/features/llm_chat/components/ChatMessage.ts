import type { ChatMessage as ChatMessageModel } from "../llm_state.ts";

export function ChatMessage(message: ChatMessageModel): HTMLElement {
	const row = document.createElement("article");
	row.className = `chat-msg ${message.role}`;
	if (message.kind) row.classList.add(`kind-${message.kind}`);


	const text = document.createElement("p");
	text.className = "chat-msg-text";
	text.textContent = message.text;

	row.append(text);
	return row;
}
