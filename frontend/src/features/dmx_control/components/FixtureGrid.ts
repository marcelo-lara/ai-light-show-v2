import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { FixtureCard } from "./FixtureCard.ts";
import { RgbControls } from "./controls/RgbControls.ts";
import { MovingHeadControls } from "./controls/MovingHeadControls.ts";
import { UnknownControls } from "./controls/UnknownControls.ts";
import { EffectTray } from "./EffectTray.ts";

export function FixtureGrid(fixtures: FixtureVM[]): HTMLElement {
	const grid = document.createElement("div");
	grid.className = "fixture-grid";
	(grid as any)._cards = new Map<string, HTMLElement>();

	if (fixtures.length === 0) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No fixtures in backend snapshot.";
		grid.appendChild(empty);
		return grid;
	}

	for (const fixture of fixtures) {
		console.log("Rendering Card for Fixture:", fixture.id, fixture.hasRgb, fixture.hasPanTilt);
		const bodyElement = (() => {
			if (fixture.hasPanTilt) return MovingHeadControls(fixture);
			if (fixture.hasRgb) return RgbControls(fixture);
			return UnknownControls(fixture.id);
		})();

		const card = FixtureCard({ 
			fixture, 
			body: () => bodyElement, 
			footer: () => EffectTray(fixture.id) 
		});
		
		(grid as any)._cards.set(fixture.id, bodyElement);
		grid.appendChild(card);
	}

	return grid;
}

export function updateFixtureGrid(grid: HTMLElement, fixtures: FixtureVM[]) {
	const cards = (grid as any)._cards as Map<string, HTMLElement>;
	if (!cards) return;

	for (const fixture of fixtures) {
		const body = cards.get(fixture.id);
		if (body && (body as any).updateValues) {
			(body as any).updateValues(fixture.values);
		}
	}
}
