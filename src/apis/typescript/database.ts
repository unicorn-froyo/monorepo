import {
  Controller,
  DynamicModule,
  Get,
  Global,
  Injectable,
  Module,
  ServiceUnavailableException,
  type OnModuleDestroy,
  type OnModuleInit,
} from "@nestjs/common";
import type { DataSource, DataSourceOptions } from "typeorm";
import { dataSourceFromFile } from "../../data/typescript/postgresql/config.js";

export interface DatabaseOptions {
  entities?: DataSourceOptions["entities"];
  /** Injected initialized connections remain owned by the caller. */
  source?: DataSource;
  /** false disables environment configuration for isolated HTTP tests. */
  connectionFile?: string | false;
}

@Injectable()
export class Database implements OnModuleInit, OnModuleDestroy {
  private source: DataSource | undefined;
  private owned = false;

  public constructor(private readonly options: DatabaseOptions) {
    this.source = options.source;
  }

  public async onModuleInit(): Promise<void> {
    const path =
      this.options.connectionFile === false
        ? undefined
        : (this.options.connectionFile ?? process.env.POSTGRES_CONNECTION_FILE);
    if (!this.source && path) {
      this.source = dataSourceFromFile(this.options.entities, path);
      this.owned = true;
      await this.source.initialize();
    }
  }

  public async onModuleDestroy(): Promise<void> {
    if (this.owned && this.source?.isInitialized) await this.source.destroy();
  }

  public connection(): DataSource {
    if (!this.source)
      throw new ServiceUnavailableException("Database is not configured");
    return this.source;
  }

  public async ready(): Promise<{ ready: boolean }> {
    if (this.source) {
      try {
        await this.source.query("SELECT 1");
      } catch {
        throw new ServiceUnavailableException({ ready: false });
      }
    }
    return { ready: true };
  }
}

@Controller("readyz")
class ReadinessController {
  public constructor(private readonly database: Database) {}
  @Get()
  public ready(): Promise<{ ready: boolean }> {
    return this.database.ready();
  }
}

@Global()
@Module({})
export class DatabaseModule {
  public static register(options: DatabaseOptions): DynamicModule {
    return {
      module: DatabaseModule,
      providers: [
        { provide: Database, useFactory: () => new Database(options) },
      ],
      exports: [Database],
      controllers: [ReadinessController],
    };
  }
}
