import { selectFixtures } from "../../shared/state/selectors.ts";
import { toFixtureVM } from "./adapters/fixture_vm.ts";

export function selectFixtureVms() {
	const fixtures = selectFixtures();
	console.log("Selecting Fixture VMs from Raw:", Object.keys(fixtures));
	const vms = Object.values(fixtures).map(toFixtureVM);
	console.log("Mapped VMs:", vms.length);
	return vms;
}
