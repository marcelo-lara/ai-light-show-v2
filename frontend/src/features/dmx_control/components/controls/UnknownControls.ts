import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { throttle } from "../../../../shared/utils/throttle.ts";

export function UnknownControls(fixtureId: string): HTMLElement {
	const state = { ch1: 0, ch2: 0, ch3: 0, ch4: 0 };
	const send = throttle((values: Record<string, number>) => setFixtureValues(fixtureId, values), 16);

	const wrap = document.createElement("div");
	wrap.className = "control-stack";

	for (const key of ["ch1", "ch2", "ch3", "ch4"] as const) {
		wrap.appendChild(
			Slider({
				label: key,
				min: 0,
				max: 255,
				value: state[key],
				onInput: (value) => {
					state[key] = value;
					send({ ...state });
				},
				onCommit: (value) => {
					state[key] = value;
					setFixtureValues(fixtureId, { ...state });
				},
			}),
		);
	}

	return wrap;
}
