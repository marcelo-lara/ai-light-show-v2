import { ChatMessage } from "./ChatMessage.ts";
import type { ChatMessage as ChatMessageModel } from "../llm_state.ts";

export function ChatHistory(messages: ChatMessageModel[], streamingText: string): HTMLElement {
	const box = document.createElement("div");
	box.className = "chat-history";

	if (messages.length === 0 && !streamingText) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "";
		box.appendChild(empty);
		return box;
	}

	for (const message of messages) box.appendChild(ChatMessage(message));

	if (streamingText) {
		const streaming = document.createElement("article");
		streaming.className = "chat-msg assistant streaming";
		const title = document.createElement("p");
		title.className = "chat-msg-title";
		title.textContent = "Assistant";
		const text = document.createElement("p");
		text.className = "chat-msg-text";
		text.textContent = streamingText;
		streaming.append(title, text);
		box.appendChild(streaming);
	}

	queueMicrotask(() => {
		box.scrollTop = box.scrollHeight;
	});

	return box;
}
