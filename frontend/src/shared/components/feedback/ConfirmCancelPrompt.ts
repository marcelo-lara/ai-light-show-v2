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
		title.className = "confirm-cancel-prompt-title";
		title.textContent = options.title ?? "Confirm action";

		const message = document.createElement("p");
		message.className = "confirm-cancel-prompt-message";
		message.textContent = options.message;

		const actions = document.createElement("div");
		actions.className = "confirm-cancel-prompt-actions";

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
		body.className = "confirm-cancel-prompt-body card card-outlined";
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
