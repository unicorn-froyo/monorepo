import "reflect-metadata";
import type { Type } from "@nestjs/common";
import { NestFactory } from "@nestjs/core";
import {
  ExpressAdapter,
  type NestExpressApplication,
} from "@nestjs/platform-express";
import type { NextFunction, Request, Response } from "express";

/** Creates a portable Nest application with the shared HTTP response policy. */
export async function createApi(
  rootModule: Type<unknown>,
): Promise<NestExpressApplication> {
  const app = await NestFactory.create<NestExpressApplication>(
    rootModule,
    new ExpressAdapter(),
    { logger: false },
  );
  app.disable("x-powered-by");
  app.use((request: Request, response: Response, next: NextFunction) => {
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
  await app.init();
  return app;
}
