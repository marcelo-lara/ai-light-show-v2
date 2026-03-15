import { Button } from "../controls/Button.ts";

export type ConfirmCancelPromptOptions = {
	title?: string;
	message: string;
	confirmLabel?: string;
	cancelLabel?: string;
};

export function ConfirmCancelPrompt(options: ConfirmCancelPromptOptions): Promise<boolean> {
	const confirmLabel = options.confirmLabel ?? "Confirm";
	const cancelLabel = options.cancelLabel ?? "Cancel";

	if (!("HTMLDialogElement" in globalThis)) {
		return Promise.resolve(window.confirm(`${options.title ? `${options.title}\n\n` : ""}${options.message}`));
	}

	return new Promise((resolve) => {
		const dialog = document.createElement("dialog");
		dialog.className = "confirm-cancel-prompt";

		const title = document.createElement("h3");
		title.textContent = options.title ?? "Confirm action";
		title.style.margin = "0";
		title.style.fontSize = "1rem";

		const message = document.createElement("p");
		message.textContent = options.message;
		message.style.margin = "0";
		message.style.fontSize = "0.9rem";
		message.style.color = "var(--muted)";

		const actions = document.createElement("div");
		actions.style.display = "flex";
		actions.style.justifyContent = "flex-end";
		actions.style.gap = "8px";

		actions.append(
			Button({
				caption: cancelLabel,
				bindings: {
					onClick: () => dialog.close("cancel"),
				},
			}),
			Button({
				caption: confirmLabel,
				state: "primary",
				bindings: {
					onClick: () => dialog.close("confirm"),
				},
			}),
		);

		const body = document.createElement("div");
		body.style.display = "flex";
		body.style.flexDirection = "column";
		body.style.gap = "12px";
		body.append(title, message, actions);

		dialog.appendChild(body);
		dialog.addEventListener("cancel", () => dialog.close("cancel"));
		dialog.addEventListener(
			"close",
			() => {
				const confirmed = dialog.returnValue === "confirm";
				dialog.remove();
				resolve(confirmed);
			},
			{ once: true },
		);

		document.body.appendChild(dialog);
		dialog.showModal();
	});
}