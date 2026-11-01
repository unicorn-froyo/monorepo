import { parseArgs } from "node:util";
import { startServer } from "./server.js";

(async (): Promise<void> => {
  const { values } = parseArgs({
    options: { port: { type: "string", default: "8080" } },
  });
  const port = Number(values.port);
  if (
    !/^\d+$/.test(values.port!) ||
    !Number.isInteger(port) ||
    port < 0 ||
    port > 65535
  )
    throw new Error("Invalid HTTP port");
  await startServer(port);
})();
