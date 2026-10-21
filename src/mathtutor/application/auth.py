"""Accounts and server-side login sessions (spec 07, ruling R2)."""

from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.application.errors import Conflict, DatabaseBusy, InvalidInput, Unauthorized
from mathtutor.store.db import is_lock_error, write_transaction
from mathtutor.store.models import User, WebSession

SESSION_LIFETIME = timedelta(days=14)
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")
PASSWORD_MIN, PASSWORD_MAX = 8, 128
_LOGIN_FAILED = "Username or password is incorrect."


@dataclass(frozen=True)
class LoginResult:
    user_id: int
    token: str
    csrf_token: str
    expires_at: datetime


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_username(username: str) -> str:
    return username.strip().lower()


class AuthService:
    def __init__(self, sessions: sessionmaker[Session], clock: Callable[[], datetime]) -> None:
        self._sessions = sessions
        self._clock = clock
        self._hasher = PasswordHasher()
        # Verified against when the user is unknown, so both failures take similar time.
        self._dummy_hash = self._hasher.hash(secrets.token_urlsafe(16))

    def register(self, username: str, password: str) -> LoginResult:
        name = normalize_username(username)
        if not USERNAME_RE.fullmatch(name):
            raise InvalidInput(
                "Usernames are 3–32 characters: lowercase letters, digits and underscores."
            )
        if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
            raise InvalidInput(f"Passwords are {PASSWORD_MIN}–{PASSWORD_MAX} characters.")
        password_hash = self._hasher.hash(password)  # slow: done before any lock is held
        with self._write() as db:
            if db.scalar(select(User.id).where(User.username == name)) is not None:
                raise Conflict("That username is taken.", code="username_taken")
            user = User(username=name, password_hash=password_hash, created_at=self._clock())
            db.add(user)
            try:
                db.flush()
            except IntegrityError:
                raise Conflict("That username is taken.", code="username_taken") from None
            return self._new_session(db, user.id)

    def login(self, username: str, password: str) -> LoginResult:
        name = normalize_username(username)
        # Read and verify without the write lock: argon2 is deliberately slow.
        with self._sessions() as db:
            user = db.scalar(select(User).where(User.username == name))
            user_id = None if user is None else user.id
            stored_hash = self._dummy_hash if user is None else user.password_hash
        if not self._verify(stored_hash, password) or user_id is None:
            raise Unauthorized(_LOGIN_FAILED, code="login_failed")
        new_hash = (
            self._hasher.hash(password) if self._hasher.check_needs_rehash(stored_hash) else None
        )
        with self._write() as db:
            if new_hash is not None:
                db.execute(update(User).where(User.id == user_id).values(password_hash=new_hash))
            return self._new_session(db, user_id)

    def resolve(self, token: str) -> tuple[int, str] | None:
        """``(user_id, csrf_token)`` for an unexpired session, else ``None``. Read-only."""
        with self._sessions() as db:
            row = db.scalar(select(WebSession).where(WebSession.token_hash == _hash_token(token)))
            if row is None or row.expires_at < self._clock():
                return None  # expired rows are inert; logout or a later sweep removes them
            return row.user_id, row.csrf_token

    def username(self, user_id: int) -> str | None:
        with self._sessions() as db:
            return db.scalar(select(User.username).where(User.id == user_id))

    def logout(self, token: str) -> None:
        with self._write() as db:
            db.execute(delete(WebSession).where(WebSession.token_hash == _hash_token(token)))

    @contextmanager
    def _write(self) -> Iterator[Session]:
        """A write transaction; a lock past busy_timeout becomes ``DatabaseBusy`` (503)."""
        try:
            with write_transaction(self._sessions) as db:
                yield db
        except OperationalError as exc:
            if is_lock_error(exc):
                raise DatabaseBusy("The database is busy. Please try again.") from exc
            raise

    def _verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def _new_session(self, db: Session, user_id: int) -> LoginResult:
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = self._clock()
        expires_at = now + SESSION_LIFETIME
        db.add(
            WebSession(
                token_hash=_hash_token(token),
                user_id=user_id,
                csrf_token=csrf_token,
                created_at=now,
                expires_at=expires_at,
            )
        )
        return LoginResult(user_id, token, csrf_token, expires_at)
