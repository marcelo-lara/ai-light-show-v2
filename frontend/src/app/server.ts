type RenderOptions = {
  bootstrap: unknown;
};

export function renderDocument(opts: RenderOptions): string {
  const bootstrapJson = JSON.stringify(opts.bootstrap ?? {}).replaceAll("<", "\\u003c");

  return `<!doctype html>
<html lang="en" data-theme="dark">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AI Light Show v2</title>
    <link rel="stylesheet" href="/src/app/themes.css" />
    <link rel="stylesheet" href="/src/app/AppShell.css" />
    <link rel="stylesheet" href="/src/shared/components/layout/Sidebar.css" />
    <link rel="stylesheet" href="/src/shared/components/layout/RightPanel.css" />
    <link rel="stylesheet" href="/src/shared/components/layout/List.css" />
    <link rel="stylesheet" href="/src/shared/components/controls/Dropdown.css" />
    <link rel="stylesheet" href="/src/shared/components/controls/Slider.css" />
    <link rel="stylesheet" href="/src/shared/components/chords_panel/ChordsPanel.css" />
    <link rel="stylesheet" href="/src/shared/components/song_player/ui/SongPlayer.css" />
    <link rel="stylesheet" href="/src/features/show_control/ShowControl.css" />
    <link rel="stylesheet" href="/src/features/show_builder/ShowBuilder.css" />
    <link rel="stylesheet" href="/src/features/song_analysis/SongAnalysis.css" />
    <link rel="stylesheet" href="/src/features/dmx_control/DmxControl.css" />
    <link rel="stylesheet" href="/src/features/llm_chat/LlmChat.css" />
  </head>
  <body>
    <div id="app"></div>
    <script>window.__BOOTSTRAP_STATE__ = ${bootstrapJson};</script>
    <script type="module" src="/app.js"></script>
  </body>
</html>`;
}
