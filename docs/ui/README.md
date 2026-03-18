# UI Docs (LLM Index)

Use this file first for UI tasks. Keep prompts short and reference exact assets by path.

## Primary files

- Workflow intent: [UX_User_Flow.md](./UX_User_Flow.md)
- Future behavior target: [UI_Future_state.md](./UI_Future_state.md)
- Shared song-player behavior: [LoFi mockups/common_player.md](./LoFi%20mockups/common_player.md)

## LoFi mockups (layout references)

- Show Control: [LoFi mockups/1 Show Control.png](./LoFi%20mockups/1%20Show%20Control.png)
- Song Analysis: [LoFi mockups/2 Song Analysis.png](./LoFi%20mockups/2%20Song%20Analysis.png)
- Show Builder: [LoFi mockups/3 Show Builder.png](./LoFi%20mockups/3%20Show%20Builder.png)
- DMX Control: [LoFi mockups/4 DMX Control.png](./LoFi%20mockups/4%20DMX%20Control.png)
- Editable source: [LoFi mockups/Web UI Lo-Fi.ai](./LoFi%20mockups/Web%20UI%20Lo-Fi.ai)

## Token-friendly usage

- Do not inline binary image data in prompts.
- Cite only the specific screen file(s) needed for the task.
- Treat LoFi files as layout references.
  - Pink annotation text is for reference/intent only and is never rendered in UI.
  - Annotation text and annotation colors are never copied into final HTML, DOM labels, or production CSS.
  - Do not create DOM elements from instructional labels in mockups (for example: `time`, `fixture`, `effect`, `duration`, `delete`, `preview`, `edit` when shown as annotation text).
  - Do not copy annotation colors from mockups into production UI.
- Use frontend token/style rules from [frontend/README.md](../../frontend/README.md).
- Never use mono fonts, unless strictly specified.
- Prioritize Flexbox, do not use Grid unless strictly necessary.
- For DMX layout tasks, use `4 DMX Control.png` plus `common_player.md` and request structure parity (not color/dimension parity).

## Explicit implementation directives

- Use CUBE CSS in frontend code; do not introduce BEM class patterns (`__`, `--`).
- CUBE model in this repo: Composition uses `l-`/`o-`, Utilities use `u-`, Blocks use semantic component names, Exceptions use `is-`/`has-`.
- Keep component structures plain; avoid wrapper-over-wrapper nesting unless required for semantics, accessibility, or behavior.
- Do not add padding or gap values unless explicitly required by the task or LoFi constraints.
- In `frontend/src/features`, use shared controls (`Button`, `Dropdown`, `Slider`, `Toggle`) for interaction elements.
- Keep feature CSS layout-only where possible; do not style shared control internals (`.btn`, `.input-shell`, `.input-field`, `.dropdown`, `.toggle`, `.slider-row`).
- Keep active/selected visuals shared and token-driven via `frontend/src/app/themes.css` (`.is-active`, `.is-selected`).
- Do not add feature-local visual state classes for common controls (for example feature-specific `.selected` or custom active border variants).
- For playlist/list rows containing info + actions, structure as two-column flex rows with actions aligned to the end.
