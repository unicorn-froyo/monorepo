import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import { applicationSources, run, validateLcov } from "./coverage-runner.mjs";

test("selects portable application sources and rejects an empty scope", () => {
  assert.deepEqual(
    applicationSources([
      "tools/example.ts",
      "tools/example.test.ts",
      "tools/tests/helper.ts",
      "../external/vendor.ts",
      "/sandbox/generated.ts",
    ]),
    ["tools/example.ts"],
  );
  assert.throws(() => applicationSources(["only.test.ts"]), /no workspace application/);
});

test("validates parseable, portable, exact LCOV source scope", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ts-lcov-"));
  const report = path.join(directory, "lcov.info");
  fs.writeFileSync(report, "TN:\nSF:tools/example.ts\nDA:1,1\nend_of_record\n");
  validateLcov(report, ["tools/example.ts"]);
  assert.throws(() => validateLcov(report, ["tools/missing.ts"]), /source scope mismatch/);
  fs.writeFileSync(report, "TN:\nSF:/sandbox/example.ts\nend_of_record\n");
  assert.throws(() => validateLcov(report, ["tools/example.ts"]), /not portable/);
  fs.writeFileSync(report, "");
  assert.throws(() => validateLcov(report, ["tools/example.ts"]), /no records/);
});

test("preserves and validates LCOV before returning a threshold failure", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ts-coverage-"));
  const output = path.join(directory, "reports");
  const scratch = path.join(directory, "scratch");
  const calls = [];
  const spawn = (_executable, args) => {
    calls.push(args);
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(
      path.join(output, "lcov.info"),
      "TN:\nSF:tools/unused.ts\nDA:1,0\nLF:1\nLH:0\nend_of_record\n",
    );
    return { status: 1 };
  };
  const status = run(
    [
      "--c8",
      "c8",
      "--entry-point",
      "tools/test.js",
      "--minimum",
      "100",
      "--source",
      "tools/unused.ts",
    ],
    { TEST_UNDECLARED_OUTPUTS_DIR: output, TEST_TMPDIR: scratch },
    spawn,
  );
  assert.equal(status, 1);
  assert.ok(fs.existsSync(path.join(output, "lcov.info")));
  assert.ok(calls[0].includes("--all"));
  assert.ok(calls[0].includes("--include=tools/unused.js"));
});
