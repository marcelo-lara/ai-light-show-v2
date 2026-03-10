import type { ChatMessage as ChatMessageModel } from "../llm_state.ts";

export function ChatMessage(message: ChatMessageModel): HTMLElement {
	const row = document.createElement("article");
	row.className = `chat-msg ${message.role}`;
	if (message.kind) row.classList.add(`kind-${message.kind}`);

	const role = document.createElement("span");
	role.className = "chat-msg-role";
	role.textContent = message.role;

	const text = document.createElement("p");
	text.className = "chat-msg-text";
	text.textContent = message.text;

	row.append(role, text);
	return row;
}
