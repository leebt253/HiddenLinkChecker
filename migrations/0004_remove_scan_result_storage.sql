-- Move existing URL history, then remove persisted scan results and scan state.
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

DO $$ BEGIN
	IF to_regclass('public.link_checks') IS NOT NULL THEN
		INSERT INTO url_checks (id, user_id, url, checked_at)
		SELECT id, user_id, submitted_url, created_at
		FROM link_checks
		ON CONFLICT (id) DO NOTHING;
	END IF;
END $$;

DROP TABLE IF EXISTS link_results;
DROP TABLE IF EXISTS link_checks;

DROP TYPE IF EXISTS link_visibility;
DROP TYPE IF EXISTS link_element_type;
DROP TYPE IF EXISTS link_check_status;

COMMIT;