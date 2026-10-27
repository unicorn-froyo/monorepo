#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const options = { sources: [] };
for (let index = 2; index < process.argv.length; index += 2) {
  const flag = process.argv[index];
  const value = process.argv[index + 1];
  if (flag === "--source") options.sources.push(value);
  else if (flag === "--prettier") options.prettier = value;
  else if (flag === "--mode") options.mode = value;
  else throw new Error(`unknown argument: ${flag}`);
}

if (!options.prettier || !["check", "write"].includes(options.mode) || options.sources.length === 0) {
  throw new Error("--prettier, --mode, and at least one --source are required");
}

let sources;
if (options.mode === "write") {
  const workspace = process.env.BUILD_WORKSPACE_DIRECTORY;
  if (!workspace) throw new Error("write mode must be run with bazel run");
  sources = options.sources.map((source) => path.join(workspace, source));
} else {
  const scratch = fs.mkdtempSync(path.join(process.env.TEST_TMPDIR ?? os.tmpdir(), "prettier-"));
  sources = options.sources.map((source) => {
    const destination = path.join(scratch, source);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
    return destination;
  });
}

const result = spawnSync(options.prettier, [`--${options.mode}`, ...sources], { stdio: "inherit" });
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
