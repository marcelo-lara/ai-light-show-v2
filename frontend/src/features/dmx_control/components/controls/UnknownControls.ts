import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { throttle } from "../../../../shared/utils/throttle.ts";
import type { FixtureControlHandle, FixtureValues } from "./control_types.ts";

export function UnknownControls(fixtureId: string): FixtureControlHandle {
	const channels = ["ch1", "ch2", "ch3", "ch4"] as const;
	const state = { ch1: 0, ch2: 0, ch3: 0, ch4: 0 };
	const send = throttle((values: Record<string, number>) => setFixtureValues(fixtureId, values), 16);

	const wrap = document.createElement("div");
	wrap.className = "control-stack";
	const sliders: Array<ReturnType<typeof Slider>> = [];

	for (const key of channels) {
		const slider = Slider({
			label: key,
			min: 0,
			max: 255,
			step: 1,
			value: state[key],
			onInput: (value) => {
				state[key] = value;
				send({ ...state });
			},
			onCommit: (value) => {
				state[key] = value;
				setFixtureValues(fixtureId, { ...state });
			},
		});
		sliders.push(slider);
		wrap.appendChild(slider.root);
	}

	const updateValues = (values: FixtureValues) => {
		for (const [index, key] of channels.entries()) {
			if (values[key] !== undefined) {
				sliders[index]?.setValue(Number(values[key]));
			}
		}
	};

	const dispose = () => {
		for (const slider of sliders) {
			slider.dispose();
		}
	};

	return {
		root: wrap,
		updateValues,
		dispose,
	};
}
