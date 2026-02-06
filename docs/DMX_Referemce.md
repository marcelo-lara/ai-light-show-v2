# DMX Fixtures Control Reference

## DMX Fixtures

### Par Can Light

### Moving Head


## Point of Interest (POI)

- POIs are named spots like "piano", "wall", "table", etc. 
- These POIs are static and can also be called "subject"

Important Note:
- Each moving head has its own pan/tilt values to the same POI.

### Action

An action is a light effect (like Fade In, Fade Out, Move, Chase)

### Chaser

A Chaser is a an effect that could involve more than one fixture in a timely sequence.
Example: "left-to-right_blue-chase" 
  -> at beat 1, the parcan_pl turns blue then starts to fade.
  -> at beat 2, the parcan_l turns blue and start to fade, while parcan_pl still fading.
  -> at beat 3, the parcan_r turns blue and start to fade, while parcan_pl almost fades out and parcan_l continues to fade.
  -> at beat 4, the parcan_pr turns blue and start to fade, while parcan_pl is off (fade completed out) and the same sequence continues on other parcans.

### Scene