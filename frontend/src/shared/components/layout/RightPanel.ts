import { StatusCard } from "../feedback/StatusCard.ts";
import { LlmChatView } from "../../../features/llm_chat/LlmChatView.ts";

export function RightPanel(): HTMLElement {
	const panel = document.createElement("aside");
	panel.className = "right-panel";
	panel.append(StatusCard(), LlmChatView());
	return panel;
}
