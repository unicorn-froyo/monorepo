import { readFileSync } from "node:fs";
import "reflect-metadata";
import { DataSource, type DataSourceOptions } from "typeorm";

/** Create a bounded TypeORM connection; Flyway alone owns schema changes. */
export function dataSourceFromFile(
  entities: NonNullable<DataSourceOptions["entities"]> = [],
  path = process.env.POSTGRES_CONNECTION_FILE,
): DataSource {
  if (!path) throw new Error("PostgreSQL connection file is not configured");
  const settings = JSON.parse(readFileSync(path, "utf8"));
  if (settings.format_version !== 1)
    throw new Error("Unsupported PostgreSQL connection format");
  if (
    !Number.isInteger(settings.port) ||
    settings.port < 1 ||
    settings.port > 65535
  )
    throw new Error("Invalid PostgreSQL port");
  if (
    !["disable", "require", "verify-ca", "verify-full"].includes(
      settings.sslmode,
    )
  )
    throw new Error("Unsupported PostgreSQL TLS policy");
  for (const key of ["host", "database", "user", "password"]) {
    if (typeof settings[key] !== "string" || !settings[key])
      throw new Error("Invalid PostgreSQL connection setting");
  }
  return new DataSource({
    type: "postgres",
    entities,
    synchronize: false,
    migrationsRun: false,
    logging: false,
    host: settings.host,
    port: settings.port,
    username: settings.user,
    password: settings.password,
    database: settings.database,
    ssl:
      settings.sslmode === "disable"
        ? false
        : {
            rejectUnauthorized: settings.sslmode !== "require",
            ...(settings.sslmode === "verify-ca"
              ? { checkServerIdentity: () => undefined }
              : {}),
          },
    poolSize: 5,
    connectTimeoutMS: 5000,
    extra: { idleTimeoutMillis: 30000, statement_timeout: 10000 },
  });
}
