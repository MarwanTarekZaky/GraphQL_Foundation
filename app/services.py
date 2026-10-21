""""Business Logic layer: the single source of truth for domain rules.

GraphQL resolvers, REST routes, or scripts call these functions.
They never talk to database directly.
"""

from app.database import(
    create_review,
    delete_review,
    update_user_nickname,
)

from app.events import publish_review_created


MIN_STARS = 1
MAX_STARS = 5


class AuthenticationError(Exception):
    pass


class ValidationError(Exception):
    pass


def require_user(user: dict | None) -> dict:
    if user is None:
        raise AuthenticationError("You must be logged in to do this.")
    return user


async def write_review(
    user: dict | None,
    episode: str,
    stars: int,
    commentary: str | None,
) -> dict:
    author = require_user(user)
    
    if not MIN_STARS <= stars <= MAX_STARS:
        raise ValidationError(
            f"Stars must be between {MIN_STARS} and {MAX_STARS}."
        )
    
    saved_review = await create_review(
        episode=episode,
        stars=stars,
        commentary=commentary,
        author_id=author["id"],
    )

    await publish_review_created(saved_review)

    return saved_review


async def remove_review(
    user: dict | None,
    review_id: str,
) -> dict | None:
    author = require_user(user)
    
    #Ownership check: only the author can delete their review
    return await delete_review(
        review_id=review_id,
        author_id=author["id"],
    )


async def change_nickname(user: dict | None, nickname: str) -> dict:
    author = require_user(user)

    nickname = nickname.strip()
    if not nickname:
        raise ValidationError("Nickname cannot be empty.")

    return await update_user_nickname(
        user_id=author["id"],
        nickname=nickname,
    )
