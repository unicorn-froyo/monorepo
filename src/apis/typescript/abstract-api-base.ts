import express, { type Application } from "express";

/** Base class for HTTP APIs implemented with Express. */
export abstract class AbstractApiBase {
  public readonly app: Application;

  protected constructor() {
    this.app = express();
    this.app.disable("x-powered-by");
    this.app.use((request, response, next) => {
      response.set({
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
      });
      if (request.secure) {
        response.set("Strict-Transport-Security", "max-age=31536000");
      }
      next();
    });
    this.configureRoutes();
  }

  protected abstract configureRoutes(): void;
}
