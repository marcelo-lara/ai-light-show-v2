export type FixtureValues = Record<string, number | string>;

export type FixtureControlHandle = {
  root: HTMLElement;
  updateValues: (values: FixtureValues) => void;
  dispose: () => void;
};

export type PanTiltControlHandle = {
  root: HTMLElement;
  activate: () => void;
  updatePanTilt: (pan: number, tilt: number) => void;
  updatePoiTarget: (pan: number | null, tilt: number | null) => void;
  dispose: () => void;
};

export type DisposableElementHandle = {
  root: HTMLElement;
  dispose: () => void;
};
