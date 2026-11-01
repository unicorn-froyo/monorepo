import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import type { ConnectionOptions } from "node:tls";
import { dataSourceFromFile } from "./config.js";

test("validates private connection settings, bounded pools and TLS policy", () => {
  const settings = JSON.parse(
    readFileSync(process.env.POSTGRES_CONNECTION_FILE!, "utf8"),
  );
  const path = join(
    mkdtempSync(join(process.env.TEST_TMPDIR!, "config-")),
    "connection.json",
  );
  const source = dataSourceFromFile();
  assert.equal(source.options.poolSize, 5);
  assert.equal(source.options.synchronize, false);
  assert.equal(source.options.migrationsRun, false);
  for (const [key, value] of [
    ["format_version", 2],
    ["port", 0],
    ["port", 65536],
    ["port", "5432"],
    ["sslmode", "prefer"],
    ["host", ""],
    ["password", null],
  ]) {
    writeFileSync(
      path,
      JSON.stringify({ ...settings, [key as string]: value }),
    );
    assert.throws(() => dataSourceFromFile([], path));
  }
  for (const sslmode of ["disable", "require", "verify-full"]) {
    writeFileSync(path, JSON.stringify({ ...settings, sslmode }));
    const options = dataSourceFromFile([], path).options;
    assert.ok(options.type === "postgres");
    assert.deepEqual(
      options.ssl,
      sslmode === "disable"
        ? false
        : { rejectUnauthorized: sslmode === "verify-full" },
    );
  }
  writeFileSync(path, JSON.stringify({ ...settings, sslmode: "verify-ca" }));
  const options = dataSourceFromFile([], path).options;
  assert.ok(options.type === "postgres");
  const ssl = options.ssl as ConnectionOptions;
  assert.equal(ssl.rejectUnauthorized, true);
  assert.equal(ssl.checkServerIdentity!("ignored", {} as never), undefined);
  assert.throws(() => dataSourceFromFile([], ""), /not configured/);
  writeFileSync(path, "{");
  assert.throws(() => dataSourceFromFile([], path));
});

test("authenticates a real bounded pool and rejects bad credentials", async () => {
  const source = await dataSourceFromFile().initialize();
  try {
    assert.equal(
      (await source.query("SELECT current_user AS role"))[0].role,
      "app",
    );
  } finally {
    await source.destroy();
  }
  const settings = JSON.parse(
    readFileSync(process.env.POSTGRES_CONNECTION_FILE!, "utf8"),
  );
  const path = join(process.env.TEST_TMPDIR!, "invalid-connection.json");
  writeFileSync(path, JSON.stringify({ ...settings, password: "incorrect" }));
  const invalid = dataSourceFromFile([], path);
  await assert.rejects(invalid.initialize(), /password authentication failed/);
  assert.equal(invalid.isInitialized, false);
});
