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
import { selectFixtureVms } from "../features/dmx_control/fixture_selectors.ts";

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
	let currentMain: HTMLElement = renderMain();
	main.appendChild(currentMain);
	let right = RightPanel();

	layout.append(sidebar, main, right);
	root.appendChild(layout);

	const renderRoute = () => {
		const nextSidebar = Sidebar();
		layout.replaceChild(nextSidebar, sidebar);
		sidebar = nextSidebar;

		currentMain = renderMain();
		main.replaceChildren(currentMain);
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
		console.log("BackendStore updated, current route:", getUiState().route);
		const vms = selectFixtureVms();
		console.log(`Store update: ${vms.length} fixtures available`);

		if (getUiState().route === "dmx_control") {
			// If we previously had 0 fixtures and now have some, force a full re-render
			// to replace the "No fixtures" message with the actual grid.
			const wasEmpty = main.innerText.includes("No fixtures in backend snapshot");
			
			if (wasEmpty && vms.length > 0) {
				console.log("Fixtures arrived, forcing full re-render of Grid");
				currentMain = renderMain();
				main.replaceChildren(currentMain);
			} else if (currentMain && (currentMain as any).updateFixtures) {
				console.log("Performing partial update for DMX Control");
				(currentMain as any).updateFixtures(vms);
			} else {
				console.log("No partial update available, re-rendering DmxControlView");
				currentMain = renderMain();
				main.replaceChildren(currentMain);
			}
		} else {
			currentMain = renderMain();
			main.replaceChildren(currentMain);
		}
		refreshSongPlayer();
		renderRight();
	});

	subscribeLlmState(() => {
		renderRight();
	});
}
