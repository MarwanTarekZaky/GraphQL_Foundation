from fastapi import HTTPException, Request

from app.database import get_user_by_token

async def authenticate(request: Request):
    authorization = request.headers.get("Authorization")
    
    if authorization is None:
        raise HTTPException(
            status_code= 401,
            detail="Authorization header missing",
        )
    
    scheme, _, token = authorization.partition(" ")
    
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header",
        )
    
    user = await get_user_by_token(token)
    
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    
    return user