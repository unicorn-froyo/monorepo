import express, { type Application } from "express";

/** Base class for HTTP APIs implemented with Express. */
export abstract class AbstractApiBase {
  public readonly app: Application;

  protected constructor() {
    this.app = express();
    this.configureRoutes();
  }

  protected abstract configureRoutes(): void;
}
