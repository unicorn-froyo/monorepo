import { runCoverage } from "./coverage-runner.js";

export function main(argv: string[]): number {
  try {
    const result = runCoverage(argv);
    return result.status ?? 1;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`TypeScript coverage failed: ${message}`);
    return 2;
  }
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
