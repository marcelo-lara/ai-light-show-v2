import { StatusCard } from "../feedback/StatusCard.ts";
import { LlmChatView } from "../../../features/llm_chat/LlmChatView.ts";

export function RightPanel(): HTMLElement {
	const panel = document.createElement("aside");
	panel.className = "right-panel";
	const statusCard = StatusCard();
	panel.append(statusCard, LlmChatView());
	const cleanup = (statusCard as unknown as { _cleanup?: () => void })._cleanup;
	if (cleanup) {
		(panel as unknown as { _cleanup: () => void })._cleanup = cleanup;
	}
	return panel;
}
