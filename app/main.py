from fastapi import FastAPI, Depends
from starlette.requests import HTTPConnection
from fastapi.middleware.gzip import GZipMiddleware

from app.graphql_http import GraphQLOverHTTPRouter
from app.schema import schema
from app.auth import get_current_user
from app.services import get_email
from app.loaders import create_loaders

from fastapi.staticfiles import StaticFiles

from app.storage import AVATAR_DIR
from app.uploads import router as uploads_router


app = FastAPI()

# Compress JSON responses for clients that send `Accept-Encoding: gzip`.
app.add_middleware(GZipMiddleware, minimum_size=1000)



async def get_context(connection: HTTPConnection):
    return {
        "request": connection,
        "user": await get_current_user(connection),
        **create_loaders(),
    }


graphql_app = GraphQLOverHTTPRouter(
    schema,
    context_getter=get_context,
    # GET is allowed for queries only (cache-friendly); mutations require POST.
    allow_queries_via_get=True,
)



app.include_router(
    graphql_app,
    prefix="/graphql",
)

app.include_router(uploads_router)

app.mount(
    "/media/avatars",
    StaticFiles(directory=AVATAR_DIR),
    name="avatars",
)

# A second entry point (REST) that reuses the same authorization rule.
@app.get("/users/{user_id}/email")
async def user_email(
    user_id: int,
    viewer: dict | None = Depends(get_current_user),
):
    return {
        "email": await get_email(viewer=viewer, user_id=user_id),
    }


@app.get("/")
async def root():
    return {
        "message": "GraphQL server is running",
        "graphql": "/graphql",
    }