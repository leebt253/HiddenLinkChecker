-- Create the minimal checked URL history table for new databases.
BEGIN;

CREATE TABLE IF NOT EXISTS url_checks (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
	url TEXT NOT NULL,
	checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
	CONSTRAINT url_checks_url_length CHECK (char_length(url) BETWEEN 1 AND 8192)
);

CREATE INDEX IF NOT EXISTS url_checks_user_history_idx
	ON url_checks (user_id, checked_at DESC);

COMMIT;