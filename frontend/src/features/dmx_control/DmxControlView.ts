import { selectFixtureVms } from "./fixture_selectors.ts";
import { FixtureGrid } from "./components/FixtureGrid.ts";

export function DmxControlView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";

	const title = document.createElement("h1");
	title.textContent = "DMX Control";

	const fixtures = selectFixtureVms();
	const grid = FixtureGrid(fixtures);

	wrap.append(title, grid);
	return wrap;
}
