import { createApi } from "../../typescript/api-base.js";
import { entities } from "../../../data/example/widgets/typescript/models.js";
import { WidgetsModule } from "./get-widgets.js";

import type { NestExpressApplication } from "@nestjs/platform-express";

export async function startServer(
  port = 8080,
  host = "0.0.0.0",
): Promise<NestExpressApplication> {
  const app = await createApi(WidgetsModule, { entities });
  try {
    await app.listen(port, host);
  } catch (error) {
    await app.close();
    throw error;
  }
  app.enableShutdownHooks();
  return app;
}
