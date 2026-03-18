import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const checklistPath = path.join(ROOT, "checklist.md");
const resultsPath = path.join(ROOT, "artifacts", "playwright-results.json");
const summaryPath = path.join(ROOT, "artifacts", "checklist-summary.md");
const dmxSummaryPath = path.resolve(ROOT, "..", "dmx-node", "artifacts", "summary.json");

function parseChecklist(markdown) {
  const lines = markdown.split(/\r?\n/);
  const entries = [];
  let currentSection = "";

  for (const line of lines) {
    if (line.startsWith("## ")) {
      currentSection = line.replace(/^##\s+/, "").trim();
      continue;
    }

    if (!line.startsWith("|")) continue;
    if (line.includes("Case ID") || line.includes("---")) continue;

    const cells = line
      .split("|")
      .slice(1, -1)
      .map((cell) => cell.trim());

    if (cells.length !== 7) continue;

    const [caseId, featureArea, scenario, expectedOutcome, implementationStatus, automationStatus, blocking] = cells;
    entries.push({
      section: currentSection,
      caseId,
      featureArea,
      scenario,
      expectedOutcome,
      implementationStatus,
      automationStatus,
      blocking,
    });
  }

  return entries;
}

function collectSpecs(suite, collected) {
  for (const childSuite of suite.suites ?? []) {
    collectSpecs(childSuite, collected);
  }

  for (const spec of suite.specs ?? []) {
    const caseMatch = spec.title.match(/^\[([A-Z0-9-]+)\]/);
    if (!caseMatch) continue;

    const results = [];
    for (const test of spec.tests ?? []) {
      for (const result of test.results ?? []) {
        results.push(result.status);
      }
    }

    const status = results.includes("failed") || results.includes("timedOut")
      ? "failed"
      : results.includes("passed")
        ? "passed"
        : results.includes("skipped")
          ? "skipped"
          : "missing";

    collected.push({
      caseId: caseMatch[1],
      title: spec.title.replace(/^\[[A-Z0-9-]+\]\s*/, ""),
      status,
    });
  }
}

function readPlaywrightStatuses() {
  if (!fs.existsSync(resultsPath)) return new Map();

  const json = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
  const collected = [];
  for (const suite of json.suites ?? []) {
    collectSpecs(suite, collected);
  }

  return new Map(collected.map((entry) => [entry.caseId, entry.status]));
}

function buildSummary(entries, statuses) {
  const evaluated = entries.map((entry) => {
    const playwrightStatus = statuses.get(entry.caseId);
    const result = entry.automationStatus === "automated"
      ? (playwrightStatus ?? "missing")
      : entry.automationStatus;
    return { ...entry, result };
  });

  const counts = {
    automatedPassed: evaluated.filter((entry) => entry.result === "passed").length,
    automatedFailed: evaluated.filter((entry) => entry.result === "failed").length,
    automatedMissing: evaluated.filter((entry) => entry.result === "missing").length,
    automatedSkipped: evaluated.filter((entry) => entry.result === "skipped").length,
    manual: evaluated.filter((entry) => entry.result === "manual").length,
    pending: evaluated.filter((entry) => entry.result === "pending").length,
  };

  const lines = [
    "# Browser Regression Summary",
    "",
    `- Automated passed: ${counts.automatedPassed}`,
    `- Automated failed: ${counts.automatedFailed}`,
    `- Automated missing: ${counts.automatedMissing}`,
    `- Automated skipped: ${counts.automatedSkipped}`,
    `- Manual checklist items: ${counts.manual}`,
    `- Pending checklist items: ${counts.pending}`,
    "",
    "| Case ID | Area | Automation | Result | Scenario |",
    "| --- | --- | --- | --- | --- |",
  ];

  for (const entry of evaluated) {
    lines.push(`| ${entry.caseId} | ${entry.featureArea} | ${entry.automationStatus} | ${entry.result} | ${entry.scenario} |`);
  }

  lines.push("");
  lines.push("Artifacts:");
  lines.push("- HTML report: `tests/browser/artifacts/html-report/`");
  lines.push("- Raw Playwright JSON: `tests/browser/artifacts/playwright-results.json`");
  lines.push("- JUnit XML: `tests/browser/artifacts/junit.xml`");
  lines.push("- Videos, traces, screenshots: `tests/browser/artifacts/test-results/`");

  if (fs.existsSync(dmxSummaryPath)) {
    const dmxSummary = JSON.parse(fs.readFileSync(dmxSummaryPath, "utf8"));
    lines.push("- DMX node summary: `tests/dmx-node/artifacts/summary.json`");
    lines.push("");
    lines.push("DMX capture:");
    lines.push(`- Captured packets: ${dmxSummary.packet_count ?? 0}`);
    lines.push(`- Stored frames: ${dmxSummary.stored_frames ?? 0}`);
  }

  return `${lines.join("\n")}\n`;
}

fs.mkdirSync(path.dirname(summaryPath), { recursive: true });

const checklist = parseChecklist(fs.readFileSync(checklistPath, "utf8"));
const statuses = readPlaywrightStatuses();
const summary = buildSummary(checklist, statuses);

fs.writeFileSync(summaryPath, summary, "utf8");
console.log(summary);
