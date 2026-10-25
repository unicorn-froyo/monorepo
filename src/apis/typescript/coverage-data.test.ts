import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

test("coverage suites receive declared runtime data", () => {
  const runfiles = process.env["TEST_SRCDIR"];
  const workspace = process.env["TEST_WORKSPACE"];
  assert.ok(runfiles);
  assert.ok(workspace);
  const fixture = join(runfiles, workspace, "src/apis/typescript/coverage_fixture.txt");
  const expected = process.env["COVERAGE_FIXTURE_EXPECTED"] ?? "coverage runtime data";
  assert.equal(readFileSync(fixture, "utf8").trim(), expected);
});
