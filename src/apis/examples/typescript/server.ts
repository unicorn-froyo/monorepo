import { createApi } from "../../typescript/api-base.js";
import { WidgetsModule } from "./get-widgets.js";

import type { NestExpressApplication } from "@nestjs/platform-express";

export async function startServer(
  port = 8080,
  host = "0.0.0.0",
): Promise<NestExpressApplication> {
  const app = await createApi(WidgetsModule);
  await app.listen(port, host);
  return app;
}

/* c8 ignore next */
if (require.main === module) void startServer();
