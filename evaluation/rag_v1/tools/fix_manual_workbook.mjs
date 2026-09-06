import { FileBlob, SpreadsheetFile } from "file:///C:/Users/lenovo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const [workbookPath] = process.argv.slice(2);
if (!workbookPath) {
  throw new Error("用法: node fix_manual_workbook.mjs <workbook.xlsx>");
}

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheet = workbook.worksheets.getItem("题库");

const expectedFormulas = Array.from({ length: 71 }, (_, index) => {
  const row = index + 2;
  return [`=IF(COUNTA(P${row}:U${row})<6,"未评分",IF(OR(W${row}="P0",W${row}="P1"),"不通过",IF(V${row}>=85,"通过","不通过")))`];
});
sheet.getRange("X2:X72").formulas = expectedFormulas;

const formulas = sheet.getRange("X2:X72").formulas;
for (let index = 0; index < formulas.length; index += 1) {
  const row = index + 2;
  const expected = expectedFormulas[index][0];
  if (formulas[index][0] !== expected) {
    throw new Error(`X${row} 公式校验失败`);
  }
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);
console.log(JSON.stringify({ workbook: workbookPath, fixedRange: "题库!X2:X72", rowsVerified: formulas.length }));
