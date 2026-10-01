from typing import Generator, Optional
from fastapi import Header, HTTPException, status

def get_db() -> Generator:
    """
    Dependency Injection for Database Session.
    Will be connected with SQLAlchemy Session local in P1-INFRA-02.
    """
    db = None
    try:
        yield db
    finally:
        pass

def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Dependency Injection Skeleton for Current User.
    Will be connected with JWT validation in P1-INFRA-03.
    """
    if not authorization:
        return None
    return {"username": "skeleton_user"}
