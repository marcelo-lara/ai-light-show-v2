import type { ChatMessage as ChatMessageModel } from "../llm_state.ts";

export function ChatMessage(message: ChatMessageModel): HTMLElement {
	const row = document.createElement("article");
	row.className = `chat-msg ${message.role}`;

	const role = document.createElement("strong");
	role.textContent = message.role;

	const text = document.createElement("p");
	text.textContent = message.text;

	row.append(role, text);
	return row;
}
