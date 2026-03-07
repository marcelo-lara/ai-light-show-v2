import { selectFixtureVms } from "./fixture_selectors.ts";
import { FixtureGrid, updateFixtureGrid } from "./components/FixtureGrid.ts";

export function DmxControlView(): HTMLElement {
	console.log("DmxControlView rendering...");
	const wrap = document.createElement("section");
	wrap.className = "view";

	const fixtures = selectFixtureVms();
	console.log("Fixtures in View:", fixtures.length);
	const grid = FixtureGrid(fixtures);

	wrap.append(grid);

	// Expose update method
	(wrap as any).updateFixtures = (fixtureVms: any[]) => {
		updateFixtureGrid(grid, fixtureVms);
	};

	return wrap;
}
