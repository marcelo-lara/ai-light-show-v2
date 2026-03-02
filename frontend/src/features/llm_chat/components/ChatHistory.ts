import { ChatMessage } from "./ChatMessage.ts";
import type { ChatMessage as ChatMessageModel } from "../llm_state.ts";

export function ChatHistory(messages: ChatMessageModel[], streamingText: string): HTMLElement {
	const box = document.createElement("div");
	box.className = "chat-history";

	if (messages.length === 0 && !streamingText) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No chat yet.";
		box.appendChild(empty);
		return box;
	}

	for (const message of messages) box.appendChild(ChatMessage(message));

	if (streamingText) {
		const streaming = document.createElement("article");
		streaming.className = "chat-msg assistant streaming";
		streaming.innerHTML = `<strong>assistant</strong><p>${escapeHtml(streamingText)}</p>`;
		box.appendChild(streaming);
	}

	return box;
}

function escapeHtml(value: string): string {
	return value
		.replaceAll("&", "&amp;")
		.replaceAll("<", "&lt;")
		.replaceAll(">", "&gt;");
}
