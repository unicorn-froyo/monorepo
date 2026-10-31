import assert from "node:assert/strict";
import {
  Controller,
  Get,
  HttpCode,
  InternalServerErrorException,
  Module,
} from "@nestjs/common";
import { test } from "node:test";
import request from "supertest";

import { createApi } from "./api-base.js";

@Controller("health")
class HealthController {
  @Get()
  @HttpCode(204)
  public health(): void {}

  @Get("error")
  public error(): never {
    throw new InternalServerErrorException("unavailable");
  }
}

@Module({ controllers: [HealthController] })
class HealthModule {}

test("registers routes", async (t) => {
  const app = await createApi(HealthModule);
  t.after(() => app.close());
  const response = await request(app.getHttpServer()).get("/health");
  assert.equal(response.status, 204);
});

test("hardens routes and missing endpoints", async (t) => {
  const app = await createApi(HealthModule);
  t.after(() => app.close());
  for (const [path, status] of [
    ["/health", 204],
    ["/missing", 404],
    ["/health/error", 500],
  ] as const) {
    const response = await request(app.getHttpServer()).get(path);
    assert.equal(response.status, status);
    assert.equal(response.headers["x-content-type-options"], "nosniff");
    assert.equal(response.headers["x-frame-options"], "DENY");
    assert.equal(response.headers["referrer-policy"], "no-referrer");
    assert.equal(
      response.headers["permissions-policy"],
      "camera=(), microphone=(), geolocation=()",
    );
    assert.equal(response.headers["strict-transport-security"], undefined);
    assert.equal(response.headers["x-powered-by"], undefined);
  }
});

test("sets HSTS on HTTPS when the proxy is trusted", async (t) => {
  const app = await createApi(HealthModule);
  t.after(() => app.close());
  app.set("trust proxy", "loopback");
  const response = await request(app.getHttpServer())
    .get("/missing")
    .set("X-Forwarded-Proto", "https");
  assert.equal(
    response.headers["strict-transport-security"],
    "max-age=31536000",
  );
});

test("does not trust a spoofed HTTPS forwarding header", async (t) => {
  const app = await createApi(HealthModule);
  t.after(() => app.close());
  const response = await request(app.getHttpServer())
    .get("/health")
    .set("X-Forwarded-Proto", "https");
  assert.equal(response.headers["strict-transport-security"], undefined);
});
