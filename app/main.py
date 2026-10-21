from fastapi import FastAPI
from starlette.requests import HTTPConnection
from app.graphql_http import GraphQLOverHTTPRouter

from app.schema import schema
from app.auth import get_current_user

app = FastAPI()


async def get_context(connection: HTTPConnection):
    authorization = connection.headers.get("Authorization")

    return {
        "request": connection,
        "user": await get_current_user(connection),
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


@app.get("/")
async def root():
    return {
        "message": "GraphQL server is running",
        "graphql": "/graphql",
    }