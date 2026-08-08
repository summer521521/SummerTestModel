import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const run = path.resolve(process.argv[process.argv.indexOf("--run-dir") + 1]);
const output = path.join(run, "scores.xlsx");
const renderDir = path.join(run, "workbook_renders");
await fs.mkdir(renderDir, { recursive: true });

const summary = JSON.parse(await fs.readFile(path.join(run, "summary_v2.json"), "utf8"));
const workbook = Workbook.create();
function addOverview() {
const overview = workbook.worksheets.add("Overview");
overview.showGridLines = false;
overview.getRange("A1:H1").merge();
overview.getRange("A1").values = [["SummerTestModel V2 综合评测工作簿"]];
overview.getRange("A2:B7").values = [
  ["Run ID", summary.run_id],
  ["Models", summary.model_count],
  ["Local models", summary.local_models],
  ["Cloud models", summary.cloud_models],
  ["Records", summary.record_count],
  ["Status counts", JSON.stringify(summary.status_counts)],
];
overview.getRange("A9:B9").values = [["Track", "Records"]];
const tracks = Object.entries(summary.track_counts);
overview.getRange(`A10:B${9 + tracks.length}`).values = tracks;
overview.getRange("D9:G9").values = [["Track", "Leader", "Score", "Coverage"]];
const leaderRows = [];
for (const track of ["core", "reasoning", "code", "translation", "long_context", "vision", "ocr", "safety", "tool", "embedding", "performance", "robustness"]) {
  const leader = (summary.leaders?.[track] || [])[0];
  if (leader) leaderRows.push([track, leader.model, `${leader.score}/${leader.max_score}`, leader.coverage]);
}
if (leaderRows.length) overview.getRange(`D10:G${9 + leaderRows.length}`).values = leaderRows;
overview.getRange("A1:H1").format = { fill: "#0F766E", font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "center" };
overview.getRange("A9:B9").format = { fill: "#D1FAE5", font: { bold: true, color: "#065F46" } };
overview.getRange("D9:G9").format = { fill: "#DBEAFE", font: { bold: true, color: "#1E3A8A" } };
overview.getRange("A1:H20").format.wrapText = true;
overview.getRange("A1:H20").format.font = { name: "Aptos", size: 10 };
overview.getRange("A1:H1").format.font = { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" };
overview.getRange("A1:H20").format.borders = { preset: "outside", style: "thin", color: "#CBD5E1" };
overview.getRange("A:A").format.columnWidth = 18;
overview.getRange("B:B").format.columnWidth = 58;
overview.getRange("D:D").format.columnWidth = 18;
overview.getRange("E:E").format.columnWidth = 42;
overview.getRange("F:G").format.columnWidth = 16;
overview.freezePanes.freezeRows(9);
if (tracks.length > 0) {
  const chart = overview.charts.add("bar", overview.getRange(`A9:B${9 + tracks.length}`));
  chart.title = "Records by track";
  chart.hasLegend = false;
  chart.setPosition("I2", "Q18");
}
}

const csvMap = {
  Scores: "all_results.csv",
  Core: "core_scores.csv", Planning: "planning_scores.csv", Reasoning: "reasoning_scores.csv", Code: "code_scores.csv", Translation: "translation_scores.csv",
  LongContext: "long_context_scores.csv", Vision: "vision_scores.csv", OCR: "ocr_scores.csv", Safety: "safety_scores.csv",
  Tools: "tool_scores.csv", Embedding: "embedding_scores.csv", Performance: "performance.csv", Failures: "failures.csv",
};
for (const [sheetName, fileName] of Object.entries(csvMap)) {
  const file = path.join(run, fileName);
  const csv = await fs.readFile(file, "utf8").catch(() => "");
  if (!csv.trim()) {
    const sheet = workbook.worksheets.add(sheetName);
    sheet.getRange("A1:B2").values = [["status", "no records"], ["source", fileName]];
    continue;
  }
  await workbook.fromCSV(csv, { sheetName });
}
const manifest = JSON.parse(await fs.readFile(path.join(run, "model_manifest.json"), "utf8"));
const manifestSheet = workbook.worksheets.add("ModelManifest");
const manifestFields = ["name", "digest", "size", "parameter_size", "quantization_level", "family", "local_or_cloud", "capabilities", "detected_capabilities"];
const manifestValues = [manifestFields, ...manifest.map(m => manifestFields.map(k => Array.isArray(m[k]) ? m[k].join(", ") : (m[k] ?? "")))];
manifestSheet.getRangeByIndexes(0, 0, manifestValues.length, manifestFields.length).values = manifestValues;
addOverview();

for (const sheet of workbook.worksheets.items) {
  sheet.showGridLines = false;
  const used = sheet.getUsedRange();
  if (used) {
    used.format.font = { name: "Aptos", size: 9 };
    used.format.wrapText = sheet.name === "Overview";
    used.format.borders = { preset: "outside", style: "thin", color: "#CBD5E1" };
    const header = sheet.getRangeByIndexes(0, 0, 1, Math.max(1, used.columnCount));
    header.format = { fill: "#0F766E", font: { bold: true, color: "#FFFFFF" }, wrapText: true };
    const widths = {
      model: 34, digest: 16, profile: 18, task_id: 16, status: 20,
      score: 12, max_score: 12, normalized_score: 14, local_or_cloud: 14,
      legacy_status: 20, offline_status: 20, offline_note: 34,
      raw_response_path: 32, parameter_size: 14, quantization: 14,
      capabilities: 32, detected_capabilities: 32, declared_capabilities: 32,
    };
    const labels = header.values[0] || [];
    for (let column = 0; column < labels.length; column += 1) {
      const label = String(labels[column] ?? "").replace(/^\uFEFF/, "");
      sheet.getRangeByIndexes(0, column, Math.max(1, used.rowCount), 1).format.columnWidth = widths[label] ?? 14;
    }
    sheet.freezePanes.freezeRows(1);
  }
}
const inspect = await workbook.inspect({ kind: "workbook,sheet,table,drawing", maxChars: 16000, tableMaxRows: 4, tableMaxCols: 8, tableMaxCellChars: 80 });
await fs.writeFile(path.join(run, "workbook_inspect.json"), JSON.stringify(inspect, null, 2));
for (const sheet of workbook.worksheets.items) {
  // Large imported detail tables exceed this runtime's bitmap limit. Their
  // dimensions and values are inspected above; render every compact sheet.
  const used = sheet.getUsedRange();
  if (sheet.name === "Scores" || (used && used.rowCount > 100)) continue;
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(renderDir, `${sheet.name}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(output);
console.log(JSON.stringify({ output, sheets: workbook.worksheets.items.map(s => s.name), renderDir }));
