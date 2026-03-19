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
    const diagnosticsAttachments = {};
    for (const test of spec.tests ?? []) {
      for (const result of test.results ?? []) {
        results.push(result.status);
        for (const entry of result.attachments ?? []) {
          if (entry.name === "show-builder-diagnostics" || entry.name === "dmx-diagnostics") {
            diagnosticsAttachments[entry.name] ??= entry;
          }
        }
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
      diagnosticsAttachments,
    });
  }
}

function readDiagnosticsFromAttachment(attachment) {
  if (!attachment) return null;

  try {
    if (attachment.path && fs.existsSync(attachment.path)) {
      return JSON.parse(fs.readFileSync(attachment.path, "utf8"));
    }
    if (attachment.body) {
      const body = String(attachment.body);
      if (body.trim().startsWith("{")) {
        return JSON.parse(body);
      }
      return JSON.parse(Buffer.from(body, "base64").toString("utf8"));
    }
  } catch {
    return null;
  }

  return null;
}

function readPlaywrightStatuses() {
  if (!fs.existsSync(resultsPath)) {
    return {
      statuses: new Map(),
      diagnostics: new Map(),
    };
  }

  const json = JSON.parse(fs.readFileSync(resultsPath, "utf8"));
  const collected = [];
  for (const suite of json.suites ?? []) {
    collectSpecs(suite, collected);
  }

  return {
    statuses: new Map(collected.map((entry) => [entry.caseId, entry.status])),
    diagnostics: new Map(
      collected
        .map((entry) => {
          const showBuilder = readDiagnosticsFromAttachment(entry.diagnosticsAttachments["show-builder-diagnostics"]);
          const dmx = readDiagnosticsFromAttachment(entry.diagnosticsAttachments["dmx-diagnostics"]);
          const diagnostics = showBuilder || dmx ? { showBuilder, dmx } : null;
          return [entry.caseId, diagnostics];
        })
        .filter(([, diagnostics]) => diagnostics !== null),
    ),
  };
}

function formatDiagnosticValue(value) {
  if (value === null || value === undefined || value === "") return "unknown";
  return String(value);
}

function buildSummary(entries, statuses, diagnostics) {
  const evaluated = entries.map((entry) => {
    const playwrightStatus = statuses.get(entry.caseId);
    const result = entry.automationStatus === "automated"
      ? (playwrightStatus ?? "missing")
      : entry.automationStatus;
    return { ...entry, result };
  });

  const cueDiagnostics = evaluated
    .filter((entry) => entry.caseId.startsWith("SB-"))
    .map((entry) => ({ caseId: entry.caseId, result: entry.result, diagnostics: diagnostics.get(entry.caseId)?.showBuilder }))
    .filter((entry) => entry.diagnostics);

  const dmxDiagnostics = evaluated
    .filter((entry) => entry.caseId === "DMX-ROUTE-VIEW" || entry.caseId === "DMX-ARM-TOGGLE" || entry.caseId === "DMX-EFFECT-PREVIEW-ENTRY")
    .map((entry) => ({ caseId: entry.caseId, result: entry.result, diagnostics: diagnostics.get(entry.caseId)?.dmx }))
    .filter((entry) => entry.diagnostics);

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

  if (cueDiagnostics.length > 0) {
    lines.push("");
    lines.push("Cue sheet diagnostics:");
    for (const entry of cueDiagnostics) {
      const snapshotCueCount = entry.diagnostics.snapshot?.cueCount;
      const cueSheetState = entry.diagnostics.cueSheetState ?? entry.diagnostics.cueSheet?.viewState;
      lines.push(
        `- ${entry.caseId} (${entry.result}): cue-sheet=${formatDiagnosticValue(cueSheetState)}, rows=${formatDiagnosticValue(entry.diagnostics.cueRowCount)}, snapshot cues=${formatDiagnosticValue(snapshotCueCount)}, ws=${formatDiagnosticValue(entry.diagnostics.wsState)}`,
      );
    }
  }

  if (dmxDiagnostics.length > 0) {
    lines.push("");
    lines.push("DMX fixture diagnostics:");
    for (const entry of dmxDiagnostics) {
      const snapshotFixtureCount = entry.diagnostics.snapshot?.fixtureCount;
      lines.push(
        `- ${entry.caseId} (${entry.result}): fixture-cards=${formatDiagnosticValue(entry.diagnostics.fixtureCardCount)}, target=${entry.diagnostics.targetFixturePresent ? "present" : "missing"}, snapshot fixtures=${formatDiagnosticValue(snapshotFixtureCount)}, ws=${formatDiagnosticValue(entry.diagnostics.wsState)}`,
      );
    }
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
const { statuses, diagnostics } = readPlaywrightStatuses();
const summary = buildSummary(checklist, statuses, diagnostics);

fs.writeFileSync(summaryPath, summary, "utf8");
console.log(summary);
