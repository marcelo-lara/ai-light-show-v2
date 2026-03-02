import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { FixtureCard } from "./FixtureCard.ts";
import { RgbControls } from "./controls/RgbControls.ts";
import { MovingHeadControls } from "./controls/MovingHeadControls.ts";
import { UnknownControls } from "./controls/UnknownControls.ts";
import { EffectTray } from "./EffectTray.ts";

export function FixtureGrid(fixtures: FixtureVM[]): HTMLElement {
	const grid = document.createElement("div");
	grid.className = "fixture-grid";

	if (fixtures.length === 0) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No fixtures in backend snapshot.";
		grid.appendChild(empty);
		return grid;
	}

	for (const fixture of fixtures) {
		const body = () => {
			if (fixture.hasPanTilt) return MovingHeadControls(fixture.id);
			if (fixture.hasRgb) return RgbControls(fixture.id);
			return UnknownControls(fixture.id);
		};

		grid.appendChild(FixtureCard({ fixture, body, footer: () => EffectTray(fixture.id) }));
	}

	return grid;
}
