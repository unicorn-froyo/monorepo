import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { test } from "node:test";
import { QueryFailedError } from "typeorm";
import { dataSourceFromFile } from "../../../typescript/postgresql/config.js";
import { entities, Outbox, Owner, Widget } from "./models.js";

test("Active Record models preserve values, relationships, transactions and permissions", async () => {
  const source = await dataSourceFromFile(entities).initialize();
  const queries: string[] = [];
  source.logger.logQuery = (query) => {
    queries.push(query);
  };
  try {
    const owner = { id: randomUUID(), name: "account 雪" };
    const widget = {
      id: randomUUID(),
      ownerId: owner.id,
      name: "雪☃",
      version: "1152921504606846977",
      amount: "1234567890123456789012.12345678",
      payload: Buffer.from([0, 255]),
      details: { value: "unicode 雪", present: false },
      createdAt: new Date("2026-10-29T12:00:00.123Z"),
      optionalText: null,
    };
    const tables = await source.query(
      "SELECT tablename FROM pg_tables WHERE schemaname = 'widgets' ORDER BY tablename",
    );
    await source.transaction(async (manager) => {
      await manager.save(Owner, owner);
      await manager.save(Widget, widget);
      await manager.save(Outbox, {
        id: randomUUID(),
        widgetId: widget.id,
        eventType: "created",
      });
    });
    queries.length = 0;
    const stored = (
      await Widget.find({
        relations: { owner: true },
        relationLoadStrategy: "join",
      })
    )[0]!;
    assert.equal(queries.length, 1);
    const { owner: loadedOwner, ...values } = stored;
    assert.equal(loadedOwner.name, owner.name);
    assert.deepEqual(values, widget);
    assert.equal(
      (
        await Owner.findOneOrFail({
          where: { id: owner.id },
          relations: { widgets: true },
        })
      ).widgets[0]!.id,
      widget.id,
    );
    assert.equal(
      (await Outbox.find({ relations: { widget: true } }))[0]!.widget.id,
      widget.id,
    );
    await assert.rejects(
      source.transaction(async (manager) => {
        const second = await manager.save(Owner, {
          id: randomUUID(),
          name: "rollback",
        });
        const record = await manager.save(Widget, {
          ...widget,
          id: randomUUID(),
          ownerId: second.id,
        });
        await manager.save(Outbox, {
          id: randomUUID(),
          widgetId: record.id,
          eventType: "created",
        });
        throw new Error("rollback");
      }),
      /rollback/,
    );
    assert.equal(await Owner.count(), 1);
    assert.equal(await Widget.count(), 1);
    assert.equal(await Outbox.count(), 1);
    assert.equal(
      (
        await Widget.update(
          { id: widget.id, version: widget.version },
          { version: "1152921504606846978" },
        )
      ).affected,
      1,
    );
    assert.equal(
      (
        await Widget.update(
          { id: widget.id, version: widget.version },
          { name: "stale" },
        )
      ).affected,
      0,
    );
    for (const [sql, code] of [
      [
        "INSERT INTO widgets.owners VALUES (gen_random_uuid(), 'account 雪')",
        "23505",
      ],
      ["INSERT INTO widgets.owners VALUES (gen_random_uuid(), NULL)", "23502"],
      [
        "INSERT INTO widgets.outbox VALUES (gen_random_uuid(), gen_random_uuid(), 'missing')",
        "23503",
      ],
      ["UPDATE widgets.widgets SET revision = 0", "23514"],
      ["CREATE TABLE widgets.forbidden (id int)", "42501"],
      ["SELECT * FROM widgets.flyway_schema_history", "42501"],
    ])
      await assert.rejects(source.query(sql!), (error: unknown) => {
        assert.ok(error instanceof QueryFailedError);
        assert.equal(error.driverError.code, code);
        return true;
      });
    assert.deepEqual(
      await source.query(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'widgets' ORDER BY tablename",
      ),
      tables,
    );
    // JavaScript Date truncates reads to milliseconds without modifying stored microseconds.
    await source.query(
      "UPDATE widgets.widgets SET created_at = '2026-10-29T12:00:00.123456Z'::timestamptz",
    );
    assert.equal(
      (await Widget.findOneByOrFail({ id: widget.id })).createdAt.toISOString(),
      "2026-10-29T12:00:00.123Z",
    );
    assert.equal(
      (
        await source.query(
          "SELECT to_char(created_at AT TIME ZONE 'UTC', 'US') AS stamp FROM widgets.widgets",
        )
      )[0].stamp,
      "123456",
    );
    await Outbox.remove(await Outbox.find());
    await Widget.remove(await Widget.find());
    assert.deepEqual(await Widget.find(), []);
    // Exercise model-level create/save and retrieve more than one page of owners in one query.
    for (let index = 101; index > 0; index--)
      await Widget.create({
        ...widget,
        id: `00000000-0000-0000-0000-${String(index).padStart(12, "0")}`,
      }).save();
    queries.length = 0;
    const sorted = await Widget.find({
      relations: { owner: true },
      relationLoadStrategy: "join",
      order: { id: "ASC" },
    });
    assert.equal(sorted.length, 101);
    assert.equal(queries.length, 1);
    assert.deepEqual(
      sorted.map((row) => row.id),
      [...sorted.map((row) => row.id)].sort(),
    );
    assert.ok(sorted.every((row) => row.owner.name === owner.name));
  } finally {
    await source.destroy();
  }
});
