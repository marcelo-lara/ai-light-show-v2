import { Sidebar } from "../shared/components/layout/Sidebar.ts";
import { RightPanel } from "../shared/components/layout/RightPanel.ts";
import { getUiState, subscribeUiState } from "../shared/state/ui_state.ts";
import { HomeView } from "../features/home/HomeView.ts";
import { SongAnalysisView } from "../features/song_analysis/SongAnalysisView.ts";
import { ShowBuilderView } from "../features/show_builder/ShowBuilderView.ts";
import { DmxControlView } from "../features/dmx_control/DmxControlView.ts";
import { subscribeBackendStore } from "../shared/state/backend_state.ts";
import { subscribeLlmState } from "../features/llm_chat/llm_state.ts";

function renderMain(): HTMLElement {
	const route = getUiState().route;
	if (route === "song_analysis") return SongAnalysisView();
	if (route === "show_builder") return ShowBuilderView();
	if (route === "dmx_control") return DmxControlView();
	return HomeView();
}

export function mountAppShell(root: HTMLElement) {
	const render = () => {
		root.innerHTML = "";

		const layout = document.createElement("div");
		layout.className = "app-shell";

		const sidebar = Sidebar();
		const main = document.createElement("main");
		main.className = "main-content";
		main.appendChild(renderMain());
		const right = RightPanel();

		layout.append(sidebar, main, right);
		root.appendChild(layout);
	};

	render();

	subscribeUiState(render);
	subscribeBackendStore(render);
	subscribeLlmState(render);
}
