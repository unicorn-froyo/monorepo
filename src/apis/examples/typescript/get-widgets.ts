import {
  Controller,
  Get,
  InternalServerErrorException,
  Module,
} from "@nestjs/common";
import { Database } from "../../typescript/database.js";
import { Widget } from "../../../data/example/widgets/typescript/models.js";

@Controller("widgets")
export class WidgetsController {
  public constructor(private readonly database: Database) {}

  @Get()
  public async getWidgets(): Promise<
    { id: string; name: string; owner: string }[]
  > {
    this.database.connection();
    try {
      const widgets = await Widget.find({
        relations: { owner: true },
        relationLoadStrategy: "join",
        order: { id: "ASC" },
      });
      return widgets.map((widget) => ({
        id: widget.id,
        name: widget.name,
        owner: widget.owner.name,
      }));
    } catch {
      throw new InternalServerErrorException("Database query failed");
    }
  }
}

@Module({ controllers: [WidgetsController] })
export class WidgetsModule {}
