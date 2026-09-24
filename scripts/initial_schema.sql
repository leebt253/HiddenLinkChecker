-- Initial PostgreSQL schema for Hidden Link Checker.
-- Apply to the application database with psql -v ON_ERROR_STOP=1 -f.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
    CREATE TYPE user_status AS ENUM ('active', 'disabled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
    CREATE TYPE link_check_status AS ENUM (
        'queued', 'running', 'completed', 'partial', 'failed'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
    CREATE TYPE link_element_type AS ENUM ('text', 'image', 'background');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
DO $$ BEGIN
    CREATE TYPE link_visibility AS ENUM ('direct', 'indirect');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_subject TEXT NOT NULL,
    email TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    status user_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ,
    CONSTRAINT users_google_subject_unique UNIQUE (google_subject),
    CONSTRAINT users_email_length CHECK (char_length(email) BETWEEN 3 AND 320),
    CONSTRAINT users_display_name_length CHECK (
        display_name IS NULL OR char_length(display_name) <= 200
    )
);

CREATE TABLE link_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    submitted_url TEXT NOT NULL,
    normalized_url TEXT,
    include_dom BOOLEAN NOT NULL DEFAULT TRUE,
    final_url TEXT,
    status link_check_status NOT NULL DEFAULT 'queued',
    http_status INTEGER,
    error_code TEXT,
    dom_reference TEXT,
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    retention_expires_at TIMESTAMPTZ,
    CONSTRAINT link_checks_user_fk FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT link_checks_submitted_url_length CHECK (
        char_length(submitted_url) BETWEEN 1 AND 8192
    ),
    CONSTRAINT link_checks_http_status_valid CHECK (
        http_status IS NULL OR http_status BETWEEN 100 AND 599
    ),
    CONSTRAINT link_checks_limitations_array CHECK (
        jsonb_typeof(limitations) = 'array'
    ),
    CONSTRAINT link_checks_completed_time_consistent CHECK (
        completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at
    ),
    CONSTRAINT link_checks_retention_time_consistent CHECK (
        retention_expires_at IS NULL OR retention_expires_at >= created_at
    )
);

CREATE TABLE link_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    link_check_id UUID NOT NULL,
    element_type link_element_type NOT NULL,
    object_reference TEXT,
    source_url TEXT NOT NULL,
    actual_url TEXT NOT NULL,
    visibility link_visibility NOT NULL,
    visible_text TEXT,
    alt_text TEXT,
    position JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT link_results_check_fk FOREIGN KEY (link_check_id)
        REFERENCES link_checks (id) ON DELETE CASCADE,
    CONSTRAINT link_results_source_url_length CHECK (
        char_length(source_url) BETWEEN 1 AND 8192
    ),
    CONSTRAINT link_results_actual_url_length CHECK (
        char_length(actual_url) BETWEEN 1 AND 8192
    ),
    CONSTRAINT link_results_position_object CHECK (
        position IS NULL OR jsonb_typeof(position) = 'object'
    )
);

CREATE INDEX link_checks_user_history_idx
    ON link_checks (user_id, created_at DESC);
CREATE INDEX link_checks_status_idx
    ON link_checks (status, created_at DESC);
CREATE INDEX link_checks_retention_idx
    ON link_checks (retention_expires_at)
    WHERE retention_expires_at IS NOT NULL;
CREATE INDEX link_results_check_idx
    ON link_results (link_check_id, created_at);
CREATE INDEX link_results_visibility_idx ON link_results (visibility);
CREATE INDEX link_results_actual_url_idx ON link_results (actual_url);

CREATE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER link_checks_set_updated_at
BEFORE UPDATE ON link_checks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
