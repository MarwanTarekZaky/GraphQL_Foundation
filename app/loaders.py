"""DataLoaders: batch the many small lookups made during one request
into a single database query, and cache the results for that request."""

from strawberry.dataloader import DataLoader

from app.database import get_users_by_ids


async def load_users(user_ids: list[int]) -> list[dict | None]:
    users = await get_users_by_ids(user_ids)
    users_by_id = {user["id"]: user for user in users}

    # A DataLoader must return one result per key, in the same order.
    return [users_by_id.get(user_id) for user_id in user_ids]


def create_loaders() -> dict:
    # New loaders for every request: their cache must never be shared
    # between requests (or between users).
    return {
        "user_loader": DataLoader(load_fn=load_users),
    }
