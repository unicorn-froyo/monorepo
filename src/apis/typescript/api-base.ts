import "reflect-metadata";
import { Module, type Type } from "@nestjs/common";
import { NestFactory } from "@nestjs/core";
import {
  ExpressAdapter,
  type NestExpressApplication,
} from "@nestjs/platform-express";
import type { NextFunction, Request, Response } from "express";

import { DatabaseModule, type DatabaseOptions } from "./database.js";

/** Creates a portable Nest application with the shared HTTP response policy. */
export async function createApi(
  rootModule: Type<unknown>,
  database: DatabaseOptions = {},
): Promise<NestExpressApplication> {
  @Module({ imports: [DatabaseModule.register(database), rootModule] })
  class ApplicationModule {}
  const app = await NestFactory.create<NestExpressApplication>(
    ApplicationModule,
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
  try {
    await app.init();
  } catch (error) {
    await app.close();
    throw error;
  }
  return app;
}
