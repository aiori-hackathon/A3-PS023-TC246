"""Bearer-token authentication for controller -> worker calls."""
import hmac
import os

from fastapi import Header, HTTPException, status


def load_token():
    token = os.environ.get("PS023_WORKER_TOKEN", "")
    if len(token) < 16:
        raise RuntimeError(
            "PS023_WORKER_TOKEN must be set to at least 16 characters"
        )
    return token


def make_auth_dependency(expected_token):
    def require_token(authorization: str = Header(default="")):
        scheme, _, supplied = authorization.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(
            supplied.encode(), expected_token.encode()
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return require_token
