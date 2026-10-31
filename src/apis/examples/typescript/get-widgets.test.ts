import assert from "node:assert/strict";
import { test } from "node:test";
import request from "supertest";

import { createApi } from "../../typescript/api-base.js";
import { WidgetsModule } from "./get-widgets.js";
import { startServer } from "./server.js";

test("hardens HTTPS and missing routes", async (t) => {
  const app = await createApi(WidgetsModule);
  t.after(() => app.close());
  app.set("trust proxy", "loopback");
  for (const [path, status] of [
    ["/widgets", 202],
    ["/missing", 404],
  ] as const) {
    const http = await request(app.getHttpServer()).get(path);
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
});

test("returns widgets", async (t) => {
  const app = await createApi(WidgetsModule);
  t.after(() => app.close());
  const response = await request(app.getHttpServer()).get("/widgets");
  assert.equal(response.status, 202);
  assert.deepEqual(response.body, []);
  assert.equal(response.headers["x-content-type-options"], "nosniff");
  const contentType = response.headers["content-type"];
  assert.ok(contentType);
  assert.match(contentType, /^application\/json/);
});

test("starts the portable HTTP server", async (t) => {
  const app = await startServer(0, "127.0.0.1");
  t.after(() => app.close());
  const response = await fetch(`${await app.getUrl()}/widgets`);
  assert.equal(response.status, 202);
  assert.deepEqual(await response.json(), []);
});
