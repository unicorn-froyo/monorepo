import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { setTimeout } from "node:timers/promises";
import request from "supertest";
import {
  entities,
  Owner,
  Widget,
} from "../../../data/example/widgets/typescript/models.js";
import { dataSourceFromFile } from "../../../data/typescript/postgresql/config.js";
import { createApi } from "../../typescript/api-base.js";
import { WidgetsModule } from "./get-widgets.js";
import { startServer } from "./server.js";

test("hardens HTTP, HTTPS and missing routes without database configuration", async (t) => {
  const app = await createApi(WidgetsModule, { connectionFile: false });
  t.after(() => app.close());
  app.set("trust proxy", "loopback");
  for (const [path, status] of [
    ["/widgets", 503],
    ["/missing", 404],
    ["/readyz", 200],
  ] as const) {
    const http = await request(app.getHttpServer()).get(path);
    assert.equal(http.status, status);
    assert.equal(http.headers["strict-transport-security"], undefined);
    const response = await request(app.getHttpServer())
      .get(path)
      .set("X-Forwarded-Proto", "https");
    assert.equal(response.status, status);
    assert.equal(response.headers["x-content-type-options"], "nosniff");
    assert.equal(response.headers["x-frame-options"], "DENY");
    assert.equal(response.headers["referrer-policy"], "no-referrer");
    assert.equal(
      response.headers["permissions-policy"],
      "camera=(), microphone=(), geolocation=()",
    );
    assert.equal(
      response.headers["strict-transport-security"],
      "max-age=31536000",
    );
    assert.equal(response.headers["x-powered-by"], undefined);
  }
  assert.deepEqual((await request(app.getHttpServer()).get("/readyz")).body, {
    ready: true,
  });
});

test("reads persisted widgets, borrows injected clients, releases failed queries and checks readiness", async () => {
  const source = await dataSourceFromFile(entities).initialize();
  const app = await createApi(WidgetsModule, { source });
  try {
    assert.deepEqual(
      (await request(app.getHttpServer()).get("/widgets")).body,
      [],
    );
    await Owner.create({
      id: "00000000-0000-0000-0000-000000000001",
      name: "account",
    }).save();
    await Widget.create({
      id: "00000000-0000-0000-0000-000000000002",
      ownerId: "00000000-0000-0000-0000-000000000001",
      name: "persisted",
      version: "1",
      amount: "1.00000000",
      payload: Buffer.from([0]),
      details: {},
      createdAt: new Date(),
      optionalText: null,
    }).save();
    const expected = [
      {
        id: "00000000-0000-0000-0000-000000000002",
        name: "persisted",
        owner: "account",
      },
    ];
    const response = await request(app.getHttpServer()).get("/widgets");
    assert.equal(response.status, 200);
    assert.deepEqual(response.body, expected);
    assert.equal(response.headers["x-content-type-options"], "nosniff");
    assert.match(response.headers["content-type"]!, /^application\/json/);
    assert.equal(
      (await request(app.getHttpServer()).get("/readyz")).status,
      200,
    );
    await app.close();
    assert.deepEqual(await source.query("SELECT 1 AS value"), [{ value: 1 }]);
    const failedApp = await createApi(WidgetsModule, { source });
    try {
      // Closing the caller-owned connection makes subsequent queries fail.
      await source.destroy();
      const failed = await request(failedApp.getHttpServer()).get("/widgets");
      assert.equal(failed.status, 500);
      assert.equal(failed.body.message, "Database query failed");
      const unready = await request(failedApp.getHttpServer()).get("/readyz");
      assert.equal(unready.status, 503);
      assert.deepEqual(unready.body, { ready: false });
    } finally {
      await failedApp.close();
    }
  } finally {
    await app.close();
    if (source.isInitialized) await source.destroy();
  }
});

test("owns startup and shutdown, rejects bad credentials and releases a failed listener", async () => {
  const observer = await dataSourceFromFile().initialize();
  const connections = async () =>
    Number(
      (
        await observer.query(
          "SELECT count(*) FROM pg_stat_activity WHERE usename = current_user",
        )
      )[0].count,
    );
  try {
    const before = await connections();
    const app = await startServer(0, "127.0.0.1");
    const port = Number(new URL(await app.getUrl()).port);
    try {
      const response = await fetch(`${await app.getUrl()}/widgets`);
      assert.equal(response.status, 200);
      assert.equal(
        ((await response.json()) as { name: string }[])[0]!.name,
        "persisted",
      );
      assert.ok((await connections()) > before);
      await assert.rejects(startServer(port, "127.0.0.1"));
    } finally {
      await app.close();
    }
    assert.equal(await connections(), before);
    const settings = JSON.parse(
      readFileSync(process.env.POSTGRES_CONNECTION_FILE!, "utf8"),
    );
    const path = join(process.env.TEST_TMPDIR!, "invalid-api-connection.json");
    writeFileSync(path, JSON.stringify({ ...settings, password: "wrong" }));
    await assert.rejects(
      createApi(WidgetsModule, { entities, connectionFile: path }),
    );
    assert.equal(await connections(), before);
  } finally {
    await observer.destroy();
  }
});

test("index serves live database updates and shuts down on SIGTERM", async () => {
  const reservation = await startServer(0, "127.0.0.1");
  const port = new URL(await reservation.getUrl()).port;
  await reservation.close();
  const child = spawn(
    process.execPath,
    [join(__dirname, "index.js"), "--port", port],
    { env: process.env, stdio: "pipe" },
  );
  let diagnostics = "";
  child.stderr.on("data", (chunk) => {
    diagnostics += chunk.toString();
  });
  const exited = once(child, "exit");
  const observer = await dataSourceFromFile().initialize();
  try {
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt++) {
      assert.equal(child.exitCode, null, diagnostics);
      try {
        ready = (await fetch(`http://127.0.0.1:${port}/readyz`)).ok;
      } catch {
        /* Still starting. */
      }
      if (ready) break;
      await setTimeout(50);
    }
    assert.ok(ready, diagnostics);
    await observer.query("UPDATE widgets.widgets SET display_name = $1", [
      "process read 雪",
    ]);
    const response = await fetch(`http://127.0.0.1:${port}/widgets`);
    assert.equal(
      ((await response.json()) as { name: string }[])[0]!.name,
      "process read 雪",
    );
  } finally {
    child.kill("SIGTERM");
    await exited;
    await observer.destroy();
  }
});

test("index rejects invalid arguments and exits on startup failure", async () => {
  for (const args of [
    ["--port=-1"],
    ["--port", "65536"],
    ["--port", "abc"],
    ["--unknown"],
    [],
  ]) {
    const child = spawn(
      process.execPath,
      [join(__dirname, "index.js"), ...args],
      {
        env: {
          ...process.env,
          POSTGRES_CONNECTION_FILE: "/missing-connection.json",
        },
        stdio: "pipe",
      },
    );
    let diagnostics = "";
    child.stderr.on("data", (chunk) => {
      diagnostics += chunk.toString();
    });
    const [code] = await once(child, "exit");
    assert.equal(code, 1, diagnostics);
    assert.match(diagnostics, /Invalid HTTP port|Unknown option|ENOENT/);
  }
});
