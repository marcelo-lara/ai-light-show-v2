import { selectFixtureVms } from "./fixture_selectors.ts";
import { FixtureGrid } from "./components/FixtureGrid.ts";
import type { FixtureVM } from "./adapters/fixture_vm.ts";

export type DmxControlViewHandle = {
	root: HTMLElement;
	updateFixtures: (fixtureVms: FixtureVM[]) => void;
	dispose: () => void;
};

export function DmxControlView(): DmxControlViewHandle {
	console.log("DmxControlView rendering...");
	const wrap = document.createElement("section");
	wrap.className = "view";

	const fixtures = selectFixtureVms();
	console.log("Fixtures in View:", fixtures.length);
	const grid = FixtureGrid(fixtures);

	wrap.append(grid.root);

	return {
		root: wrap,
		updateFixtures: (fixtureVms: FixtureVM[]) => grid.updateFixtures(fixtureVms),
		dispose: () => grid.dispose(),
	};
}
