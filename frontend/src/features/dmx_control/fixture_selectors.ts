import { selectFixtures } from "../../shared/state/selectors.ts";
import { toFixtureVM } from "./adapters/fixture_vm.ts";

export function selectFixtureVms() {
	const fixtures = selectFixtures();
	return Object.values(fixtures).map(toFixtureVM);
}
