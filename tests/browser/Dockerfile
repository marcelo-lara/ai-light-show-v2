FROM mcr.microsoft.com/playwright:v1.52.0-jammy

WORKDIR /app

COPY package.json ./package.json
RUN npm install

WORKDIR /app/tests/browser

CMD ["bash", "-lc", "mkdir -p ./artifacts && node ./scripts/wait-for-services.mjs && node ./scripts/reset-dmx-node.mjs && /app/node_modules/.bin/playwright test; status=$?; dmx_status=0; if [ $status -eq 0 ]; then node ./scripts/assert-dmx-output.mjs; dmx_status=$?; else echo '[dmx-node] Skipping DMX assertions because browser tests failed.'; fi; if [ \"${GITHUB_ACTIONS}\" = \"true\" ]; then echo '[video-convert] Skipping MP4 conversion on GitHub Actions.'; else node ./scripts/convert-videos-to-mp4.mjs; fi; node ./scripts/render-checklist-summary.mjs; if [ $status -ne 0 ]; then exit $status; fi; exit $dmx_status"]
