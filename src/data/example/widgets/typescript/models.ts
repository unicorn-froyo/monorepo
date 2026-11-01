import "reflect-metadata";
import {
  BaseEntity,
  Column,
  Entity,
  Index,
  JoinColumn,
  ManyToOne,
  OneToMany,
  PrimaryColumn,
} from "typeorm";

@Entity({ schema: "widgets", name: "owners" })
export class Owner extends BaseEntity {
  @PrimaryColumn("uuid")
  id!: string;

  @Column({ name: "display_name", type: "text", unique: true })
  name!: string;

  @OneToMany(() => Widget, (widget) => widget.owner)
  widgets!: Widget[];
}

@Entity({ schema: "widgets", name: "widgets" })
@Index("widgets_owner", ["ownerId"])
export class Widget extends BaseEntity {
  @PrimaryColumn("uuid")
  id!: string;

  @Column({ name: "owner_id", type: "uuid" })
  ownerId!: string;

  @Column({ name: "display_name", type: "text" })
  name!: string;

  // PostgreSQL bigint and numeric remain exact decimal strings.
  @Column({ name: "revision", type: "bigint", default: 1 })
  version!: string;

  @Column({ type: "numeric", precision: 30, scale: 8 })
  amount!: string;

  @Column({ type: "bytea" })
  payload!: Buffer;

  @Column({ name: "metadata", type: "jsonb" })
  details!: Record<string, unknown>;

  @Column({ name: "created_at", type: "timestamptz", precision: 6 })
  createdAt!: Date;

  @Column({ name: "optional_text", type: "text", nullable: true })
  optionalText!: string | null;

  @ManyToOne(() => Owner, (owner) => owner.widgets, { nullable: false })
  @JoinColumn({ name: "owner_id" })
  owner!: Owner;
}

@Entity({ schema: "widgets", name: "outbox" })
export class Outbox extends BaseEntity {
  @PrimaryColumn("uuid")
  id!: string;

  @Column({ name: "widget_id", type: "uuid" })
  widgetId!: string;

  @Column({ name: "event_type", type: "text" })
  eventType!: string;

  @ManyToOne(() => Widget, { nullable: false })
  @JoinColumn({ name: "widget_id" })
  widget!: Widget;
}

export const entities = [Owner, Widget, Outbox];
