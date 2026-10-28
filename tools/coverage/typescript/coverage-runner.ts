import fs from "node:fs";
import path from "node:path";
import { spawnSync, type SpawnSyncReturns } from "node:child_process";

export interface CoverageOptions {
  c8: string;
  entryPoint: string;
  minimum: string;
  sources: string[];
}

export function applicationSources(candidates: string[]): string[] {
  const sources = [...new Set(candidates)].sort().filter((candidate) => {
    const normalized = candidate.replaceAll("\\", "/");
    return (
      normalized === candidate &&
      !path.isAbsolute(candidate) &&
      !normalized.split("/").includes("..") &&
      normalized.endsWith(".ts") &&
      !normalized.endsWith(".test.ts") &&
      !normalized.split("/").includes("tests")
    );
  });
  if (sources.length === 0) {
    throw new Error(
      "srcs contains no workspace application TypeScript sources",
    );
  }
  return sources;
}

export function validateLcov(report: string, expectedSources: string[]): void {
  if (!fs.existsSync(report)) throw new Error(`c8 did not produce ${report}`);
  const text = fs.readFileSync(report, "utf8");
  const records = text
    .split("end_of_record")
    .filter((record) => record.trim() !== "");
  if (records.length === 0) throw new Error("lcov.info contains no records");
  const actual = new Set<string>();
  for (const record of records) {
    const sourceLines = record
      .split("\n")
      .filter((line) => line.startsWith("SF:"));
    if (sourceLines.length !== 1)
      throw new Error("each LCOV record must contain exactly one SF entry");
    const source = sourceLines[0]!.slice(3);
    if (
      path.isAbsolute(source) ||
      source.includes("\\") ||
      source.split("/").includes("..")
    ) {
      throw new Error(`LCOV source path is not portable: ${source}`);
    }
    actual.add(source);
  }
  const expected = new Set(expectedSources);
  const missing = [...expected].filter((source) => !actual.has(source));
  const unexpected = [...actual].filter((source) => !expected.has(source));
  if (missing.length || unexpected.length) {
    throw new Error(
      `LCOV source scope mismatch; missing=[${missing.join(", ")}], unexpected=[${unexpected.join(", ")}]`,
    );
  }
}

function parseArguments(argv: string[]): CoverageOptions {
  const options: CoverageOptions = {
    sources: [],
    c8: "",
    entryPoint: "",
    minimum: "",
  };
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (value === undefined) throw new Error(`missing value for ${flag}`);
    if (flag === "--source") options.sources.push(value);
    else if (flag === "--c8") options.c8 = value;
    else if (flag === "--entry-point") options.entryPoint = value;
    else if (flag === "--minimum") options.minimum = value;
    else throw new Error(`unknown argument: ${flag}`);
  }
  if (!options.c8 || !options.entryPoint || !options.minimum) {
    throw new Error("--c8, --entry-point, and --minimum are required");
  }
  return options;
}

export function runCoverage(
  argv: string[],
  environment: NodeJS.ProcessEnv = process.env,
  spawn: typeof spawnSync = spawnSync,
): SpawnSyncReturns<Buffer> {
  const options = parseArguments(argv);
  const sources = applicationSources(options.sources);
  const output = environment.TEST_UNDECLARED_OUTPUTS_DIR;
  const scratch = environment.TEST_TMPDIR;
  if (!output || !scratch)
    throw new Error("Bazel test output directories are required");
  fs.mkdirSync(output, { recursive: true });
  const args = [
    "--all",
    `--reports-dir=${output}`,
    `--temp-directory=${path.join(scratch, "c8")}`,
    "--check-coverage",
    `--lines=${options.minimum}`,
    "--branches=0",
    "--functions=0",
    "--statements=0",
    "--reporter=text",
    "--reporter=lcovonly",
    ...sources.map((source) => `--include=${source.slice(0, -3)}.js`),
    "--exclude=**/*.test.js",
    "node",
    options.entryPoint,
  ];
  const result = spawn(options.c8, args, {
    env: environment,
    stdio: "inherit",
  });
  validateLcov(path.join(output, "lcov.info"), sources);
  if (result.error) throw result.error;
  return result;
}
