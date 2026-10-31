import { Controller, Get, HttpCode, Module } from "@nestjs/common";

@Controller("widgets")
export class WidgetsController {
  @Get()
  @HttpCode(202)
  public getWidgets(): unknown[] {
    return [];
  }
}

@Module({ controllers: [WidgetsController] })
export class WidgetsModule {}
