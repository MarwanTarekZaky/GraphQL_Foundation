from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from starlette.requests import HTTPConnection

from app.database import get_user_by_token
from app.schema import schema


app = FastAPI()


async def get_context(connection: HTTPConnection):
    authorization = connection.headers.get("Authorization")

    user = None

    if authorization:
        scheme, _, token = authorization.partition(" ")

        if scheme.lower() == "bearer" and token:
            user = await get_user_by_token(token)

    return {
        "request": connection,
        "user": user,
    }


graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
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