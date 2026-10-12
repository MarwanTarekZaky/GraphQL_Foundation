from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from app.auth import authenticate
from app.schema import schema


app = FastAPI()


async def get_context(request: Request):
    user = await authenticate(request)
    
    return {
        "request": request,
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