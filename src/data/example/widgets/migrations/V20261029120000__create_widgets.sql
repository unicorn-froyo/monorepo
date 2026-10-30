CREATE TABLE owners (
    id UUID PRIMARY KEY,
    display_name TEXT NOT NULL UNIQUE
);

CREATE TABLE widgets (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES owners (id),
    display_name TEXT NOT NULL,
    revision BIGINT NOT NULL DEFAULT 1,
    amount NUMERIC(30, 8) NOT NULL,
    payload BYTEA NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    optional_text TEXT,
    CONSTRAINT positive_version CHECK (revision > 0)
);

CREATE INDEX widgets_owner ON widgets (owner_id);

CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    widget_id UUID NOT NULL REFERENCES widgets (id),
    event_type TEXT NOT NULL
);
