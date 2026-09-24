-- Server-side sessions and short-lived OIDC login transactions.
BEGIN;

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    CONSTRAINT user_sessions_expiry_valid CHECK (expires_at > created_at)
);

CREATE INDEX user_sessions_user_idx ON user_sessions (user_id, expires_at);
CREATE INDEX user_sessions_active_idx ON user_sessions (expires_at) WHERE revoked_at IS NULL;

CREATE TABLE oauth_login_transactions (
    state_hash BYTEA PRIMARY KEY,
    nonce_hash BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX oauth_login_transactions_expiry_idx ON oauth_login_transactions (expires_at);

COMMIT;