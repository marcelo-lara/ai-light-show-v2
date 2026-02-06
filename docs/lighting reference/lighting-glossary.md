# Lighting Glossary (DMX & Show Control)

This glossary defines common terms used across DMX lighting controllers, fixtures, and show programming.
Definitions are controller-agnostic unless otherwise stated.

---

## DMX & Addressing

**DMX (Digital Multiplex)**  
A unidirectional control protocol used to send lighting control data from a controller to fixtures.

**DMX Channel**  
A single control value (0–255) that represents one controllable parameter of a fixture.

**DMX Address**  
The starting channel number a fixture listens to within a universe.

**Universe**  
A group of 512 DMX channels. Multiple universes are used for larger systems.

**Footprint**  
The total number of DMX channels a fixture consumes in a given mode.

---

## Fixture & Patch

**Fixture**  
Any controllable lighting device (PAR, moving head, strobe, LED bar, etc.).

**Fixture Mode**  
A predefined mapping of DMX channels to parameters (e.g., 8-bit vs 16-bit pan/tilt, RGB vs RGBW).

**Patch**  
The process of assigning fixtures to universes and DMX addresses in the controller.

**Clone / Copy Fixture**  
Duplicating fixture configuration and patch information.

---

## Control & Playback

**Cue**  
A stored lighting look or state.

**Cue Stack / Sequence**  
An ordered list of cues, usually played back sequentially.

**Playback / Executor / Fader**  
A physical or virtual control used to trigger or modify cues.

**HTP (Highest Takes Precedence)**  
When multiple sources control the same channel, the highest value wins (commonly dimmers).

**LTP (Latest Takes Precedence)**  
The most recent command takes priority (commonly color, position, gobo).

---

## Looks & Structure

**Group**  
A logical collection of fixtures for fast selection.

**Palette / Preset**  
A reusable stored value for a specific attribute (color, position, gobo, etc.).

**Effect / FX**  
An automated, time-based modulation of one or more parameters.

**Chase**  
A sequence of steps that loop, often rhythm-based.

---

## Timing & Sync

**Fade Time**  
Time taken to transition between values.

**Delay**  
Wait time before a cue or parameter change starts.

**Timecode**  
External timing reference (e.g., SMPTE, MIDI) used to synchronize lighting to audio/video.

---

## Networking

**Art-Net**  
DMX-over-IP protocol using broadcast or unicast.

**Node**  
A device that converts network DMX to physical DMX outputs.
