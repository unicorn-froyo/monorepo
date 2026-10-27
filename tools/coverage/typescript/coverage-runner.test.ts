import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import {
  applicationSources,
  runCoverage,
  validateLcov,
} from "./coverage-runner.js";
import { main } from "./coverage-runner-main.js";

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
  assert.throws(
    () => applicationSources(["only.test.ts"]),
    /no workspace application/,
  );
});

test("validates portable LCOV source scope and rejects empty reports", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ts-lcov-"));
  const report = path.join(directory, "lcov.info");
  fs.writeFileSync(report, "TN:\nSF:tools/example.ts\nDA:1,1\nend_of_record\n");
  validateLcov(report, ["tools/example.ts"]);
  assert.throws(
    () => validateLcov(report, ["tools/missing.ts"]),
    /source scope mismatch/,
  );
  fs.writeFileSync(report, "TN:\nSF:/sandbox/example.ts\nend_of_record\n");
  assert.throws(
    () => validateLcov(report, ["tools/example.ts"]),
    /not portable/,
  );
  fs.writeFileSync(report, "");
  assert.throws(() => validateLcov(report, ["tools/example.ts"]), /no records/);
});

test("preserves LCOV before returning a coverage threshold failure", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ts-coverage-"));
  const output = path.join(directory, "reports");
  const scratch = path.join(directory, "scratch");
  const spawn = (_executable: string, args: readonly string[]) => {
    assert.ok(args.includes("--all"));
    assert.ok(args.includes("--include=tools/unused.js"));
    fs.mkdirSync(output, { recursive: true });
    fs.writeFileSync(
      path.join(output, "lcov.info"),
      "TN:\nSF:tools/unused.ts\nDA:1,0\nLF:1\nLH:0\nend_of_record\n",
    );
    return {
      status: 1,
      signal: null,
      output: [null, Buffer.alloc(0), Buffer.alloc(0)],
      pid: 1,
    };
  };
  const result = runCoverage(
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
    spawn as never,
  );
  assert.equal(result.status, 1);
  assert.ok(fs.existsSync(path.join(output, "lcov.info")));
});

test("main reports invalid runner inputs", () => {
  assert.equal(main([]), 2);
  assert.equal(main(["--unknown", "value"]), 2);
});
