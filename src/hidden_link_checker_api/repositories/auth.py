"""Persistence contracts and adapters for users, sessions and OIDC transactions."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from hidden_link_checker_api.domain.models import (
    GoogleIdentity,
    OAuthLoginTransaction,
    User,
    UserSession,
)


class AuthRepository(Protocol):
    """Persistence boundary for all server-side authentication state."""

    def upsert_user(self, identity: GoogleIdentity, logged_in_at: datetime) -> User:
        """Create or update a user based on the provider's stable subject."""

    def create_session(self, session: UserSession) -> None:
        """Persist a new session token hash."""

    def get_user_by_session_token(self, token: str, now: datetime) -> User | None:
        """Return the active user matched by an opaque session token."""

    def revoke_session(self, token: str, revoked_at: datetime) -> None:
        """Revoke a session without retaining token plaintext."""

    def create_oauth_transaction(self, transaction: OAuthLoginTransaction) -> None:
        """Persist a short-lived OIDC state and nonce pair."""

    def consume_oauth_transaction(self, state: str, now: datetime) -> OAuthLoginTransaction | None:
        """Return and invalidate an unexpired transaction matched by state."""


class InMemoryAuthRepository:
    """Test/development adapter; production should use PostgreSQLAuthRepository."""

    def __init__(self) -> None:
        self._users_by_subject: dict[str, User] = {}
        self._sessions: dict[bytes, UserSession] = {}
        self._transactions: dict[bytes, OAuthLoginTransaction] = {}

    def upsert_user(self, identity: GoogleIdentity, logged_in_at: datetime) -> User:
        existing_user = self._users_by_subject.get(identity.subject)
        user = User(
            id=existing_user.id if existing_user else uuid4(),
            google_subject=identity.subject,
            email=identity.email,
            display_name=identity.display_name,
            avatar_url=identity.avatar_url,
            created_at=existing_user.created_at if existing_user else logged_in_at,
            last_login_at=logged_in_at,
        )
        self._users_by_subject[identity.subject] = user
        return user

    def create_session(self, session: UserSession) -> None:
        self._sessions[session.token_hash] = session

    def get_user_by_session_token(self, token: str, now: datetime) -> User | None:
        session = self._sessions.get(UserSession.from_token(token, UUID(int=0), now).token_hash)
        if session is None or session.expires_at <= now:
            return None
        return next((user for user in self._users_by_subject.values() if user.id == session.user_id), None)

    def revoke_session(self, token: str, revoked_at: datetime) -> None:
        token_hash = UserSession.from_token(token, UUID(int=0), revoked_at).token_hash
        self._sessions.pop(token_hash, None)

    def create_oauth_transaction(self, transaction: OAuthLoginTransaction) -> None:
        self._transactions[transaction.state_hash] = transaction

    def consume_oauth_transaction(self, state: str, now: datetime) -> OAuthLoginTransaction | None:
        probe = OAuthLoginTransaction.hash_value(state)
        transaction = self._transactions.pop(probe, None)
        if transaction is None or transaction.expires_at <= now:
            return None
        return transaction


class PostgreSQLAuthRepository:
    """Production PostgreSQL adapter using parameterized queries and transactions."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def upsert_user(self, identity: GoogleIdentity, logged_in_at: datetime) -> User:
        query = """
            INSERT INTO users (google_subject, email, display_name, avatar_url, last_login_at)
            VALUES (%(subject)s, %(email)s, %(display_name)s, %(avatar_url)s, %(logged_in_at)s)
            ON CONFLICT (google_subject) DO UPDATE SET
                email = EXCLUDED.email,
                display_name = EXCLUDED.display_name,
                avatar_url = EXCLUDED.avatar_url,
                last_login_at = EXCLUDED.last_login_at
            RETURNING id, google_subject, email, display_name, avatar_url, created_at, last_login_at
        """
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, {"subject": identity.subject, "email": identity.email,
                                   "display_name": identity.display_name, "avatar_url": identity.avatar_url,
                                   "logged_in_at": logged_in_at})
            return _to_user(cursor.fetchone())

    def create_session(self, session: UserSession) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_sessions (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
                (session.user_id, session.token_hash, session.expires_at),
            )

    def get_user_by_session_token(self, token: str, now: datetime) -> User | None:
        token_hash = UserSession.from_token(token, UUID(int=0), now).token_hash
        query = """
            SELECT u.id, u.google_subject, u.email, u.display_name, u.avatar_url,
                   u.created_at, u.last_login_at
            FROM user_sessions AS session
            JOIN users AS u ON u.id = session.user_id
            WHERE session.token_hash = %s AND session.revoked_at IS NULL AND session.expires_at > %s
              AND u.status = 'active'
        """
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (token_hash, now))
            row = cursor.fetchone()
        return _to_user(row) if row else None

    def revoke_session(self, token: str, revoked_at: datetime) -> None:
        token_hash = UserSession.from_token(token, UUID(int=0), revoked_at).token_hash
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE user_sessions SET revoked_at = %s WHERE token_hash = %s AND revoked_at IS NULL",
                (revoked_at, token_hash),
            )

    def create_oauth_transaction(self, transaction: OAuthLoginTransaction) -> None:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO oauth_login_transactions (state_hash, nonce_hash, expires_at) VALUES (%s, %s, %s)",
                (transaction.state_hash, transaction.nonce_hash, transaction.expires_at),
            )

    def consume_oauth_transaction(self, state: str, now: datetime) -> OAuthLoginTransaction | None:
        state_hash = OAuthLoginTransaction.hash_value(state)
        query = """
            DELETE FROM oauth_login_transactions
            WHERE state_hash = %s AND expires_at > %s
            RETURNING state_hash, nonce_hash, expires_at
        """
        with self._connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (state_hash, now))
            row = cursor.fetchone()
        if row is None:
            return None
        return OAuthLoginTransaction(**row)

    @contextmanager
    def _connection(self) -> Iterator[psycopg.Connection[dict[str, object]]]:
        with psycopg.connect(self._database_url) as connection:
            yield connection


def _to_user(row: dict[str, object]) -> User:
    return User(
        id=row["id"], google_subject=row["google_subject"], email=row["email"],
        display_name=row["display_name"], avatar_url=row["avatar_url"],
        created_at=row["created_at"], last_login_at=row["last_login_at"],
    )