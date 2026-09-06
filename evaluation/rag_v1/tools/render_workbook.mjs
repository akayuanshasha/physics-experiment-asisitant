import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "file:///C:/Users/lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const [inputPath, outputDir] = process.argv.slice(2);
if (!inputPath || !outputDir) {
  throw new Error("用法: node render_workbook.mjs <input.xlsx> <output-dir>");
}

await fs.mkdir(outputDir, { recursive: true });
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 12000,
  tableMaxRows: 8,
  tableMaxCols: 26,
  tableMaxCellChars: 120,
});
console.log("WORKBOOK_OVERVIEW");
console.log(overview.ndjson ?? String(overview));

const summarySheet = workbook.worksheets.getItem("汇总");
const questionSheet = workbook.worksheets.getItem("题库");
console.log("SUMMARY_FORMULAS_B4_B11");
console.log(JSON.stringify(summarySheet.getRange("B4:B11").formulas));
console.log("QUESTION_FORMULAS_V2_X72");
console.log(JSON.stringify(questionSheet.getRange("V2:X72").formulas));

for (const sheet of workbook.worksheets.items) {
  const safeName = sheet.name.replace(/[\\/:*?"<>|]/g, "_");
  const preview = await workbook.render({
    sheetName: sheet.name,
    autoCrop: "all",
    scale: 1,
    format: "png",
  });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  const destination = path.join(outputDir, `${safeName}.png`);
  await fs.writeFile(destination, bytes);
  const used = sheet.getUsedRange();
  const usedAddress = used ? used.address : "";
  console.log(JSON.stringify({ sheet: sheet.name, usedRange: usedAddress, preview: destination }));
}
