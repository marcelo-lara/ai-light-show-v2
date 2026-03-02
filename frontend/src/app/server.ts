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
  </head>
  <body>
    <div id="app"></div>
    <script>window.__BOOTSTRAP_STATE__ = ${bootstrapJson};</script>
    <script type="module" src="/app.js"></script>
  </body>
</html>`;
}
