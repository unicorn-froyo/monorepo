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
