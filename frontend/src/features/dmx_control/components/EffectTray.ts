import { previewEffect } from "../fixture_intents.ts";

export function EffectTray(fixtureId: string): HTMLElement {
	const row = document.createElement("div");
	row.className = "effect-tray";

	const flash = document.createElement("button");
	flash.type = "button";
	flash.className = "btn";
	flash.textContent = "Flash";
	flash.addEventListener("click", () => previewEffect(fixtureId, "flash", 500));

	const strobe = document.createElement("button");
	strobe.type = "button";
	strobe.className = "btn";
	strobe.textContent = "Strobe";
	strobe.addEventListener("click", () => previewEffect(fixtureId, "strobe", 1000));

	const full = document.createElement("button");
	full.type = "button";
	full.className = "btn";
	full.textContent = "Full";
	full.addEventListener("click", () => previewEffect(fixtureId, "full", 800));

	row.append(flash, strobe, full);
	return row;
}
