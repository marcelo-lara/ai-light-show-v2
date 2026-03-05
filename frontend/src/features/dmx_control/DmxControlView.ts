import { selectFixtureVms } from "./fixture_selectors.ts";
import { FixtureGrid } from "./components/FixtureGrid.ts";

export function DmxControlView(): HTMLElement {
	const wrap = document.createElement("section");
	wrap.className = "view";

	const fixtures = selectFixtureVms();
	const grid = FixtureGrid(fixtures);

	wrap.append(grid);
	return wrap;
}
