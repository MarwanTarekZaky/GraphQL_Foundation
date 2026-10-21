from fastapi import HTTPException
from starlette.requests import HTTPConnection

from app.database import get_user_by_token


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
    

async def get_current_user(connection: HTTPConnection) -> dict | None:
    """Authentication: who is calling? Runs before GraphQL.

    No header -> anonymous (None). A bad header or token -> 401.
    Authorization (what the user may do) is decided later, in app/services.py.
    """
    
    authorization = connection.headers.get("Authorization")
    if authorization is None:
        return None
    
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise unauthorized("Invalid authorization header")

    user = await get_user_by_token(token)

    if user is None:
        raise unauthorized("Invalid token")

    return user