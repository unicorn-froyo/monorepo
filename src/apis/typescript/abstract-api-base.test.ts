import assert from "node:assert/strict";
import { test } from "node:test";
import request from "supertest";

import { AbstractApiBase } from "./abstract-api-base.js";

class HealthApi extends AbstractApiBase {
  public constructor() {
    super();
  }

  protected configureRoutes(): void {
    this.app.get("/health", (_request, response) => {
      response.sendStatus(204);
    });
  }
}

test("registers routes", async () => {
  const response = await request(new HealthApi().app).get("/health");
  assert.equal(response.status, 204);
});

test("hardens routes and missing endpoints", async () => {
  const app = new HealthApi().app;
  for (const path of ["/health", "/missing"]) {
    const response = await request(app).get(path);
    assert.equal(response.headers["x-content-type-options"], "nosniff");
    assert.equal(response.headers["x-frame-options"], "DENY");
    assert.equal(response.headers["referrer-policy"], "no-referrer");
    assert.equal(response.headers["permissions-policy"], "camera=(), microphone=(), geolocation=()");
    assert.equal(response.headers["strict-transport-security"], undefined);
    assert.equal(response.headers["x-powered-by"], undefined);
  }
});

test("sets HSTS on HTTPS when the proxy is trusted", async () => {
  const app = new HealthApi().app;
  app.set("trust proxy", "loopback");
  const response = await request(app).get("/missing").set("X-Forwarded-Proto", "https");
  assert.equal(response.headers["strict-transport-security"], "max-age=31536000");
});
