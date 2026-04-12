import { assertEquals } from "jsr:@std/assert";
import { activeSongEventKey, activeSongEvents, normalizeSongEvents } from "./song_events.ts";
import type { SongState } from "../../../transport/protocol.ts";

function buildSong(events: SongState["analysis"]["events"]): SongState {
  return {
    filename: "Test Song",
    analysis: { events },
  };
}

Deno.test("normalizeSongEvents drops invalid rows and sorts by time", () => {
  const song = buildSong([
    { id: "later", type: "impact_hit", start_time: 3, end_time: 4, confidence: 0.8, intensity: 0.9, section_id: "", provenance: "machine", summary: "", created_by: "", evidence_summary: "", lighting_hint: "" },
    { id: "invalid", type: "build", start_time: 2, end_time: 2, confidence: 0.8, intensity: 0.4, section_id: "", provenance: "machine", summary: "", created_by: "", evidence_summary: "", lighting_hint: "" },
    { id: "first", type: "build", start_time: 1, end_time: 2, confidence: 0.7, intensity: 0.5, section_id: "", provenance: "machine", summary: "", created_by: "", evidence_summary: "", lighting_hint: "" },
  ]);

  assertEquals(normalizeSongEvents(song), [
    { id: "first", type: "build", start_s: 1, end_s: 2, intensity: 0.5 },
    { id: "later", type: "impact_hit", start_s: 3, end_s: 4, intensity: 0.9 },
  ]);
});

Deno.test("activeSongEvents returns only the rows active at the cursor", () => {
  const events = normalizeSongEvents(buildSong([
    { id: "build", type: "build", start_time: 10, end_time: 12, confidence: 0.7, intensity: 0.5, section_id: "", provenance: "machine", summary: "", created_by: "", evidence_summary: "", lighting_hint: "" },
    { id: "drop", type: "drop", start_time: 11, end_time: 12, confidence: 0.9, intensity: 1, section_id: "", provenance: "machine", summary: "", created_by: "", evidence_summary: "", lighting_hint: "" },
    { id: "later", type: "impact_hit", start_time: 12, end_time: 13, confidence: 0.8, intensity: 0.9, section_id: "", provenance: "machine", summary: "", created_by: "", evidence_summary: "", lighting_hint: "" },
  ]));

  assertEquals(
    activeSongEvents(events, 11_500),
    [
      { id: "build", type: "build", start_s: 10, end_s: 12, intensity: 0.5 },
      { id: "drop", type: "drop", start_s: 11, end_s: 12, intensity: 1 },
    ],
  );
  assertEquals(activeSongEventKey(events, 11_500), "build|drop");
  assertEquals(activeSongEventKey(events, 12_000), "later");
});