import { Card } from "../../shared/components/layout/Card.ts";
import { ChatHistory } from "./components/ChatHistory.ts";
import { PromptInput } from "./components/PromptInput.ts";
import { getLlmState } from "./llm_state.ts";

export function LlmChatView(): HTMLElement {
	const content = document.createElement("div");
	content.className = "llm-chat";

	const state = getLlmState();
	content.append(ChatHistory(state.messages, state.streamingText), PromptInput());

	return Card(content, { title: "LLM Chat" });
}
