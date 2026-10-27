import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

const prettier = process.argv[2];

test("formatter check rejects bad layout and accepts its write output", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ts-format-"));
  const source = path.join(directory, "example.ts");
  fs.writeFileSync(source, "export const value={answer:42}\n");
  const check = () => spawnSync(prettier, ["--check", source], { encoding: "utf8" });
  assert.notEqual(check().status, 0);
  const write = spawnSync(prettier, ["--write", source], { encoding: "utf8" });
  assert.equal(write.status, 0, write.stderr);
  assert.equal(check().status, 0);
  assert.equal(fs.readFileSync(source, "utf8"), "export const value = { answer: 42 };\n");
});
