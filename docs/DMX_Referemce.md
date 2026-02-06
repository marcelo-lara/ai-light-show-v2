# DMX Fixtures Control Reference

## DMX Fixtures

### Par Can Light

### Moving Head


## Point of Interest (POI)

- POIs are named spots like "piano", "wall", "table", etc. 
- These POIs are static and can also be called "subject"

Important Note:
- Each moving head has its own pan/tilt values to the same POI.

### Effect

An effect is a channel-value sequence over time.

**Common Examples**
- Fade In: send values from 0 to 255 to the dimmer channel (or individual RGB channels).
- Fade Out: send values from 0 to 255 to the dimmer channel (or individual RGB channels).
- 

### Chaser

A Chaser is a an sequence of effects that could involve more than one fixture in a timely sequence.
Example: "left-to-right blue-chase" 
  -> at beat 1, the parcan_pl set blue to max and start fade out.
  -> at beat 2, the parcan_l set blue to max and start to fade out, while parcan_pl still fading.
  -> at beat 3, the parcan_r turns blue and start to fade, while parcan_pl almost fades out and parcan_l continues to fade.
  -> at beat 4, the parcan_pr turns blue and start to fade, while parcan_pl is off (fade completed out) and the same sequence continues on other parcans.

### Scene

A scene is a combination of effects and/or chasers to be used in one or more segments of the show.
Example: 