export type Section = {
  name: string;
  start_s: number;
  end_s: number;
};

export type SongPlayerEvent = {
  id: string;
  type: string;
  start_s: number;
  end_s: number;
  intensity: number;
};
