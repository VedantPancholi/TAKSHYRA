import hashlib
import hmac
import os
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from takshyra.db import session
from takshyra.models import Membership, Tenant, User

basic = HTTPBasic(auto_error=False)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or int(rounds) != 600_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class Identity:
    user_id: str
    username: str
    tenant_id: str
    tenant_slug: str
    role: str


def identity(
    credentials: HTTPBasicCredentials | None = Depends(basic),
    tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    db: Session = Depends(session),
) -> Identity:
    if os.getenv("APP_ENV") != "development":
        raise HTTPException(503, "Demo identity unavailable")
    if not credentials or not tenant_slug:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credentials and tenant required", headers={"WWW-Authenticate": "Basic"})
    user = db.scalar(select(User).where(User.username == credentials.username))
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials", headers={"WWW-Authenticate": "Basic"})
    membership = db.execute(
        select(Membership, Tenant)
        .join(Tenant, Membership.tenant_id == Tenant.id)
        .where(Membership.user_id == user.id, Tenant.slug == tenant_slug)
    ).first()
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tenant membership required")
    member, tenant = membership
    return Identity(user.id, user.username, tenant.id, tenant.slug, member.role)


def executor(principal: Identity = Depends(identity)) -> Identity:
    if principal.role not in {"executor", "admin"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pipeline execution permission required")
    return principal
