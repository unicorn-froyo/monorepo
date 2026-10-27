import { app } from "./get-widgets.js";

import type { Server } from "node:http";

export function startServer(port = 8080, host = "0.0.0.0"): Server {
  return app.listen(port, host);
}

/* c8 ignore next */
if (require.main === module) startServer();
