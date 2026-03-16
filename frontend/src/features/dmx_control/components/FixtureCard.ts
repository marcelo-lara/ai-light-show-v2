import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { setArm } from "../fixture_intents.ts";
import { Toggle } from "../../../shared/components/controls/Toggle.ts";

/**
 * Shared container concept.
 * Copilot: implement UIX component rendering here.
 *
 * Must expose a "body slot" for specialized controls + optional footer slot.
 */
export type FixtureCardProps = {
  fixture: FixtureVM;
  body: () => HTMLElement;
  footer?: () => HTMLElement;
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

  const armToggle = Toggle({
    label: "Armed",
    checked: props.fixture.armed,
    className: "dmx-arm-toggle",
    onChange: (checked) => {
      setArm(props.fixture.id, checked);
    },
  });

  header.append(left, armToggle.root);

  const body = document.createElement("div");
  body.className = "fixture-card-body";
  body.appendChild(props.body());

  root.append(header, body);

  if (props.footer) {
    const footer = document.createElement("footer");
    footer.className = "fixture-card-footer";
    footer.appendChild(props.footer());
    root.appendChild(footer);
  }

  return root;
}
