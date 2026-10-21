import assert from "node:assert/strict";
import { test } from "node:test";
import request from "supertest";

import { app } from "./get-widgets.js";

test("returns widgets", async () => {
  const response = await request(app).get("/widgets");
  assert.equal(response.status, 202);
  assert.deepEqual(response.body, []);
  const contentType = response.headers["content-type"];
  assert.ok(contentType);
  assert.match(contentType, /^application\/json/);
});
