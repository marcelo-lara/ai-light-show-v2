import { Sidebar } from "../shared/components/layout/Sidebar.ts";
import { RightPanel } from "../shared/components/layout/RightPanel.ts";
import { getUiState, subscribeUiState } from "../shared/state/ui_state.ts";
import { SongAnalysisView } from "../features/song_analysis/SongAnalysisView.ts";
import { ShowBuilderView } from "../features/show_builder/ShowBuilderView.ts";
import { DmxControlView } from "../features/dmx_control/DmxControlView.ts";
import { ShowControlView } from "../features/show_control/ShowControlView.ts";
import { subscribeBackendStore } from "../shared/state/backend_state.ts";
import { subscribeLlmState } from "../features/llm_chat/llm_state.ts";
import { refreshSongPlayer } from "../shared/components/song_player/SongPlayer.ts";

function renderMain(): HTMLElement {
	const route = getUiState().route;
	if (route === "song_analysis") return SongAnalysisView();
	if (route === "show_builder") return ShowBuilderView();
	if (route === "dmx_control") return DmxControlView();
	return ShowControlView();
}

export function mountAppShell(root: HTMLElement) {
	root.innerHTML = "";

	const layout = document.createElement("div");
	layout.className = "app-shell";

	let sidebar = Sidebar();
	const main = document.createElement("main");
	main.className = "main-content";
	main.appendChild(renderMain());
	let right = RightPanel();

	layout.append(sidebar, main, right);
	root.appendChild(layout);

	const renderRoute = () => {
		const nextSidebar = Sidebar();
		layout.replaceChild(nextSidebar, sidebar);
		sidebar = nextSidebar;

		main.replaceChildren(renderMain());
	};

	const renderRight = () => {
		const nextRight = RightPanel();
		layout.replaceChild(nextRight, right);
		right = nextRight;
	};

	subscribeUiState(() => {
		renderRoute();
		renderRight();
	});

	subscribeBackendStore(() => {
		if (getUiState().route === "dmx_control") {
			main.replaceChildren(renderMain());
		}
		refreshSongPlayer();
		renderRight();
	});

	subscribeLlmState(() => {
		renderRight();
	});
}
