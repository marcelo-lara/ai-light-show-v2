import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { setArm } from "../fixture_intents.ts";

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
  const props = _props;
  const root = document.createElement("article");
  root.className = "fixture-card";

  const header = document.createElement("header");
  header.className = "fixture-card-header";

  const left = document.createElement("div");
  const name = document.createElement("h3");
  name.textContent = props.fixture.name;
  const type = document.createElement("small");
  type.className = "muted";
  type.textContent = props.fixture.type;
  left.append(name, type);

  const armButton = document.createElement("button");
  armButton.type = "button";
  armButton.className = `btn ${props.fixture.armed ? "primary" : ""}`.trim();
  armButton.textContent = props.fixture.armed ? "ARMED" : "DISARMED";
  armButton.addEventListener("click", () => {
    setArm(props.fixture.id, !props.fixture.armed);
  });

  header.append(left, armButton);

  const body = document.createElement("div");
  body.className = "fixture-card-body";
  body.appendChild(props.body() as HTMLElement);

  root.append(header, body);

  if (props.footer) {
    const footer = document.createElement("footer");
    footer.className = "fixture-card-footer";
    footer.appendChild(props.footer() as HTMLElement);
    root.appendChild(footer);
  }

  return root;
}
