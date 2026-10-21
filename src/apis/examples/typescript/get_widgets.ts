import { AbstractApiBase } from "../../typescript/abstract_api_base.js";

export class GetWidgets extends AbstractApiBase {
  public constructor() {
    super();
  }

  protected configureRoutes(): void {
    this.app.get("/widgets", (_request, response) => {
      response.status(202).json([]);
    });
  }
}

export const app = new GetWidgets().app;
