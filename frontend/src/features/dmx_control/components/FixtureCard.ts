import type { FixtureVM } from "../adapters/fixture_vm.ts";

/**
 * Shared container concept.
 * Copilot: implement UIX component rendering here.
 *
 * Must expose a "body slot" for specialized controls + optional footer slot.
 */
export type FixtureCardProps = {
  fixture: FixtureVM;
  body: () => unknown; // UIX template/JSX node
  footer?: () => unknown;
};

export function FixtureCard(_props: FixtureCardProps) {
  // TODO: implement in UIX syntax (using your template conventions)
  return null;
}
