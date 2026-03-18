# Browser Regression Checklist

This checklist is derived from [`docs/ui/UX_User_Flow.md`](../../../docs/ui/UX_User_Flow.md).
It captures the intended user-facing regression surface, while the current implementation status reflects the app as it exists today.
Browser-run artifacts include per-test MP4 videos, screenshots, traces, and summary reports.

## Preparation

| Case ID | Feature Area | Scenario | Expected Visible Outcome | Implementation Status | Automation Status | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| PREP-START-UI | Preparation | Start the UI after song metadata is prepared | The browser app loads and the main navigation is available | implemented | automated | no |
| PREP-SONG-IMPORT | Preparation | Add a song into the backend songs folder | The prepared song becomes available to the application | partial | manual | no |
| PREP-ANALYZE-SONG | Preparation | Run analyzer metadata generation before entering the UI | Analysis-driven views have song metadata to render | partial | manual | no |

## Song Analysis

| Case ID | Feature Area | Scenario | Expected Visible Outcome | Implementation Status | Automation Status | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| SA-ROUTE-VIEW | Song Analysis | Open Song Analysis from the app navigation | Song Analysis renders the player plus the song structure and analysis plot regions | implemented | automated | no |
| SA-SECTION-EDIT | Song Analysis | Adjust song part labels and section boundaries | Section editing controls are available and the updates can be saved | future | pending | no |
| SA-POINT-HINTS | Song Analysis | Add, remove, or edit song point hints | Point hints can be manipulated visibly from the UI | future | pending | no |

## Show Builder

| Case ID | Feature Area | Scenario | Expected Visible Outcome | Implementation Status | Automation Status | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| SB-ROUTE-VIEW | Show Builder | Open Show Builder from the app navigation | Cue Sheet, Effect Picker, and Chaser Picker regions are visible | implemented | automated | no |
| SB-EFFECT-CUE-EDIT | Show Builder | Edit an existing effect cue from the cue sheet | The Effect Picker switches into update mode for the selected cue | implemented | automated | no |
| SB-CHASER-CUE-EDIT | Show Builder | Edit an existing chaser cue from the cue sheet | The Chaser Picker switches into update mode for the selected cue | implemented | automated | no |
| SB-CUE-DELETE-CANCEL | Show Builder | Start cue deletion and cancel at the confirmation prompt | The delete confirmation dialog appears and closes without removing the cue | implemented | automated | no |
| SB-SAVE-AS-CHASER | Show Builder | Save selected cue-sheet effects as a chaser | A chaser creation flow is visible and can be completed | future | pending | no |

## DMX Controller

| Case ID | Feature Area | Scenario | Expected Visible Outcome | Implementation Status | Automation Status | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| DMX-ROUTE-VIEW | DMX Controller | Open DMX Control from the app navigation | Fixture cards are visible with live controls | implemented | automated | no |
| DMX-ARM-TOGGLE | DMX Controller | Arm or disarm a fixture from its card | The Armed toggle updates visibly for the selected fixture | implemented | automated | no |
| DMX-EFFECT-PREVIEW-ENTRY | DMX Controller | Open the effect preview controls for a fixture | Effect selection, duration, and preview controls are visible in the fixture card | implemented | automated | no |
| DMX-POI-SET | DMX Controller | Record a moving-head POI using fixture controls | The POI interaction is visible and can be committed from the UI | partial | pending | no |

## Show Control

| Case ID | Feature Area | Scenario | Expected Visible Outcome | Implementation Status | Automation Status | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| SC-ROUTE-VIEW | Show Control | Open Show Control from the app navigation | Song Sections, cue summary, fixture effects, and transport controls are visible | implemented | automated | no |
| SC-PLAYBACK-START | Show Control | Start playback from the transport controls | Playback controls and timing readout update for the running show | partial | pending | no |
