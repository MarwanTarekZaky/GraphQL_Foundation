import os

from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from uuid import uuid4
from bson import ObjectId

from app.monitoring import DatabaseQueryCounter
load_dotenv()


MONGODB_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://localhost:27017"
)

MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "graphql_learning"
)

client = AsyncMongoClient(
    MONGODB_URL,
    event_listeners=[DatabaseQueryCounter()],
)


db = client[MONGODB_DATABASE]

user_collection = db["users"]

async def get_user_by_token(token: str):
    return await user_collection.find_one({
        "token": token
    })
    
async def get_user(user_id: int):
    return await user_collection.find_one({
        "id": user_id
    })

async def get_users_by_ids(user_ids: list[int]):
    users = []
    async for user in user_collection.find({"id": {"$in": user_ids}}):
        users.append(user)
    return users

async def get_user_full_name(user_id: int):
    user = await user_collection.find_one({
        "id": user_id
    })
    
    if user is None:
        return None
    
    return user["fullName"]

async def get_user_nickname(user_id: int):
    user = await user_collection.find_one({
        "id": user_id
    })
    
    if user is None:
        return None
    
    return user["nickname"]

review_collection = db["reviews"]

async def create_review(
    episode: str,
    stars: int,
    commentary: str | None,
    author_id: int
):
    review_document = {
        "id": str(uuid4()),
        "episode": episode,
        "stars": stars,
        "commentary": commentary,
        "authorId": author_id,
    }
    
    await review_collection.insert_one(review_document)
    
    return review_document

async def get_all_reviews():
    reviews = []
    async for review in review_collection.find():
        reviews.append(review)
    return reviews

async def find_reviews(
    author_id: int | None,
    before_id: ObjectId | None,
    limit: int,
):
    query = {}

    if author_id is not None:
        query["authorId"] = author_id

    if before_id is not None:
        query["_id"] = {"$lt": before_id}

    reviews = []
    async for review in review_collection.find(query).sort("_id", -1).limit(limit):
        reviews.append(review)
    return reviews


async def count_reviews(author_id: int | None):
    query = {}

    if author_id is not None:
        query["authorId"] = author_id

    return await review_collection.count_documents(query)

async def get_reviews_by_author(author_id: int):
    reviews = []
    async for review in review_collection.find({"authorId": author_id}):
        reviews.append(review)
    return reviews
    

async def update_user_nickname(user_id: int, nickname: str):
    await user_collection.update_one(
        {
            "id": user_id
        },
        {
            "$set": {
                "nickname": nickname,
            }
        },
    )
    
    return await user_collection.find_one({
        "id": user_id
    })
    
    
async def get_review(review_id: str):
    return await review_collection.find_one({
        "id": review_id
    })


async def delete_review(review_id: str):
    await review_collection.delete_one({
        "id": review_id
    })



upload_collection = db["uploads"]


async def create_upload(upload_id: str, owner_id: int, expires: int):
    await upload_collection.insert_one({
        "id": upload_id,
        "ownerId": owner_id,
        "expires": expires,
    })


async def get_upload(upload_id: str):
    return await upload_collection.find_one({
        "id": upload_id
    })


async def delete_upload(upload_id: str):
    await upload_collection.delete_one({
        "id": upload_id
    })


async def get_user_avatar_url(user_id: int):
    user = await user_collection.find_one({
        "id": user_id
    })

    if user is None:
        return None

    return user.get("avatarUrl")


async def get_user_email(user_id: int):
    user = await user_collection.find_one({
        "id": user_id
    })

    if user is None:
        return None

    return user.get("email")


async def update_user_avatar_url(user_id: int, avatar_url: str):
    await user_collection.update_one(
        {
            "id": user_id
        },
        {
            "$set": {
                "avatarUrl": avatar_url,
            }
        },
    )

    return await user_collection.find_one({
        "id": user_id
    })
