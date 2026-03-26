# LLM Tuning

- Date: 2026-03-25
- Goal: tune live assistant answers and proposal routing for AI Light Show v2 chat.
- Implemented MCP improvements: bar/beat lookup, exact chord lookup, typo-tolerant section matching.
- Implemented gateway improvements: query guidance, richer tool result formatting, grounded fast paths for common prompts, stricter factual answer prompts.
- Implemented frontend improvement: clear conversation button remains usable even while a proposal is pending.
- Validation completed through live frontend with chat cleared between prompts.
- Verified live outcomes:
  - intro end -> 35.820s
  - first chord F -> 51.940s at bar 29 beat 1
  - clear corus cue sheet -> proposal for 84.180s to 100.280s
  - left fixtures -> mini_beam_prism_l, parcan_l, parcan_pl
  - first instruental chaser request -> proposal for parcan_left_to_right at 35.820s for 8 repetitions
  - first verse loudness -> 57.320s to 84.180s, average 0.238286
  - fixtures at bar 21 -> mini_beam_prism_l and mini_beam_prism_r flash at 37.620s
- Important nuance: cursor answer depends on transport state. To match expected cursor result, transport was explicitly set to 37.620s before asking.
- Remaining polish if resumed: tighten final phrasing for verse-effect answer to include user-preferred "for 1 beat" wording instead of 0.896s, and optionally normalize bar.beat wording to 21.1 rather than "bar 21, beat 1".