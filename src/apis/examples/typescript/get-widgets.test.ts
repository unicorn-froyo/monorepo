import assert from "node:assert/strict";
import { test } from "node:test";
import request from "supertest";

import { app } from "./get-widgets.js";
import { startServer } from "./server.js";

test("hardens HTTPS and missing routes", async () => {
  const previousTrustProxy = app.get("trust proxy");
  app.set("trust proxy", "loopback");
  try {
    for (const [path, status] of [
      ["/widgets", 202],
      ["/missing", 404],
    ] as const) {
      const http = await request(app).get(path);
      assert.equal(http.headers["strict-transport-security"], undefined);
      const response = await request(app)
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
  } finally {
    app.set("trust proxy", previousTrustProxy);
  }
});

test("returns widgets", async () => {
  const response = await request(app).get("/widgets");
  assert.equal(response.status, 202);
  assert.deepEqual(response.body, []);
  assert.equal(response.headers["x-content-type-options"], "nosniff");
  const contentType = response.headers["content-type"];
  assert.ok(contentType);
  assert.match(contentType, /^application\/json/);
});

test("starts the portable HTTP server", async () => {
  const server = startServer(0, "127.0.0.1");
  await new Promise<void>((resolve, reject) => {
    server.once("listening", resolve);
    server.once("error", reject);
  });
  await new Promise<void>((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
});
