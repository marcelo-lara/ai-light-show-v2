import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { FixtureCard } from "./FixtureCard.ts";
import { RgbControls } from "./controls/RgbControls.ts";
import { MovingHeadControls } from "./controls/MovingHeadControls.ts";
import { UnknownControls } from "./controls/UnknownControls.ts";
import { EffectTray } from "./EffectTray.ts";
import type { FixtureControlHandle } from "./controls/control_types.ts";

export type FixtureGridHandle = {
	root: HTMLElement;
	updateFixtures: (fixtures: FixtureVM[]) => void;
	dispose: () => void;
};

function fixtureIds(fixtures: FixtureVM[]): string {
	return fixtures.map((fixture) => fixture.id).sort().join("|");
}

export function FixtureGrid(initialFixtures: FixtureVM[]): FixtureGridHandle {
	const root = document.createElement("div");
	root.className = "fixture-grid";

	let controls = new Map<string, FixtureControlHandle>();
	let currentIds = "";

	const disposeControls = () => {
		for (const control of controls.values()) {
			control.dispose();
		}
		controls.clear();
	};

	const render = (fixtures: FixtureVM[]) => {
		disposeControls();
		root.replaceChildren();

		if (fixtures.length === 0) {
			const empty = document.createElement("p");
			empty.className = "muted";
			empty.textContent = "No fixtures in backend snapshot.";
			root.appendChild(empty);
			currentIds = "";
			return;
		}

		for (const fixture of fixtures) {
			console.log("Rendering Card for Fixture:", fixture.id, fixture.hasRgb, fixture.hasPanTilt);
			const control = (() => {
				if (fixture.hasPanTilt) return MovingHeadControls(fixture);
				if (fixture.hasRgb) return RgbControls(fixture);
				return UnknownControls(fixture.id);
			})();

			const card = FixtureCard({
				fixture,
				body: () => control.root,
				footer: () => EffectTray(fixture.id),
			});

			controls.set(fixture.id, control);
			root.appendChild(card);
		}
		currentIds = fixtureIds(fixtures);
	};

	const updateFixtures = (fixtures: FixtureVM[]) => {
		const nextIds = fixtureIds(fixtures);
		if (nextIds !== currentIds) {
			render(fixtures);
			return;
		}

		for (const fixture of fixtures) {
			const control = controls.get(fixture.id);
			if (control) {
				control.updateValues(fixture.values);
			}
		}
	};

	const dispose = () => {
		disposeControls();
		root.replaceChildren();
	};

	render(initialFixtures);

	return {
		root,
		updateFixtures,
		dispose,
	};
}
