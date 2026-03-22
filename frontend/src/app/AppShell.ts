import { Sidebar } from "../shared/components/layout/Sidebar.ts";
import { RightPanel } from "../shared/components/layout/RightPanel.ts";
import { getUiState, subscribeUiState } from "../shared/state/ui_state.ts";
import { SongAnalysisView } from "../features/song_analysis/SongAnalysisView.ts";
import { ShowBuilderView } from "../features/show_builder/ShowBuilderView.ts";
import { DmxControlView } from "../features/dmx_control/DmxControlView.ts";
import { ShowControlView } from "../features/show_control/ShowControlView.ts";
import { getBackendStore, subscribeBackendStore } from "../shared/state/backend_state.ts";
import { getLlmState, isLlmActiveStatus, subscribeLlmState } from "../features/llm_chat/llm_state.ts";
import { refreshSongPlayer } from "../shared/components/song_player/SongPlayer.ts";
import { selectFixtureVms } from "../features/dmx_control/fixture_selectors.ts";
import { selectEditLock } from "../shared/state/selectors.ts";

type FixtureList = ReturnType<typeof selectFixtureVms>;

type MainViewHandle = {
	root: HTMLElement;
	updateFixtures?: (fixtures: FixtureList) => void;
	dispose?: () => void;
};

function staticView(root: HTMLElement): MainViewHandle {
	return { root };
}

function renderMain(): MainViewHandle {
	const route = getUiState().route;
	if (route === "song_analysis") return staticView(SongAnalysisView());
	if (route === "show_builder") return staticView(ShowBuilderView());
	if (route === "dmx_control") return DmxControlView();
	return staticView(ShowControlView());
}

export function mountAppShell(root: HTMLElement) {
	root.innerHTML = "";

	const layout = document.createElement("div");
	layout.className = "app-shell";

	let sidebar = Sidebar();
	const main = document.createElement("main");
	main.className = "main-content";
	let currentMain: MainViewHandle = renderMain();
	main.appendChild(currentMain.root);
	let right = RightPanel();
	let lastSongKey = getBackendStore().state.song?.filename ?? "";
	let previousEditLock = selectEditLock();

	layout.append(sidebar, main, right);
	root.appendChild(layout);

	const replaceMain = (nextView: MainViewHandle) => {
		currentMain.dispose?.();
		currentMain = nextView;
		main.replaceChildren(currentMain.root);
	};

	const renderRoute = () => {
		const nextSidebar = Sidebar();
		layout.replaceChild(nextSidebar, sidebar);
		sidebar = nextSidebar;

		replaceMain(renderMain());
	};

	const renderRight = () => {
		const nextRight = RightPanel();
		(right as unknown as { _cleanup?: () => void })._cleanup?.();
		layout.replaceChild(nextRight, right);
		right = nextRight;
		syncInteractionLocks();
	};

	const syncInteractionLocks = () => {
		const llmActive = isLlmActiveStatus(getLlmState().status);
		const showLocked = selectEditLock() === true;

		layout.dataset.llmLocked = llmActive ? "true" : "false";
		layout.dataset.showLocked = showLocked ? "true" : "false";
		sidebar.inert = llmActive;
		main.inert = llmActive;

		const statusCard = right.querySelector<HTMLElement>(".status-card");
		if (statusCard) {
			statusCard.inert = llmActive;
		}

		const llmCard = right.querySelector<HTMLElement>(".llm-card");
		if (llmCard) {
			llmCard.inert = showLocked;
			if (showLocked) {
				llmCard.setAttribute("aria-disabled", "true");
			} else {
				llmCard.removeAttribute("aria-disabled");
			}
		}
	};

	subscribeUiState(() => {
		renderRoute();
		renderRight();
	});

	subscribeBackendStore(() => {
		const route = getUiState().route;
		const songKey = getBackendStore().state.song?.filename ?? "";
		const songChanged = songKey !== lastSongKey;
		const nextEditLock = selectEditLock();
		lastSongKey = songKey;

		if (route === "dmx_control") {
			const vms = selectFixtureVms();
			if (typeof currentMain.updateFixtures === "function") {
				currentMain.updateFixtures(vms);
			} else {
				replaceMain(renderMain());
			}
		} else if (songChanged) {
			replaceMain(renderMain());
		}

		if (nextEditLock !== previousEditLock) {
			renderRight();
		}

		refreshSongPlayer();
		syncInteractionLocks();
		previousEditLock = nextEditLock;
	});

	let previousLlmStatus = getLlmState().status;
	const focusPromptInput = () => {
		requestAnimationFrame(() => {
			if (selectEditLock() === true) return;
			const input = right.querySelector<HTMLTextAreaElement>(".prompt-input");
			if (!input) return;
			input.focus({ preventScroll: true });
			const caret = input.value.length;
			input.setSelectionRange(caret, caret);
		});
	};

	subscribeLlmState(() => {
		const hadPromptFocus =
			document.activeElement instanceof HTMLElement &&
			document.activeElement.classList.contains("prompt-input");
		const nextLlmStatus = getLlmState().status;
		const interactionFinished =
			isLlmActiveStatus(previousLlmStatus) && (nextLlmStatus === "idle" || nextLlmStatus === "error");

		renderRight();
		syncInteractionLocks();

		if (hadPromptFocus || interactionFinished) {
			focusPromptInput();
		}

		previousLlmStatus = nextLlmStatus;
	});

	syncInteractionLocks();
}
