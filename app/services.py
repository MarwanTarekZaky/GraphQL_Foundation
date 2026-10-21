""""Business Logic layer: the single source of truth for domain rules.

GraphQL resolvers, REST routes, or scripts call these functions.
They never talk to database directly.
"""

from app.database import (
    create_review,
    update_user_nickname,
    create_upload,
    get_upload,
    delete_upload,
    update_user_avatar_url,
    get_review,
    delete_review,
    get_user_email,
)
from app.events import publish_review_created
from app.storage import (
    create_signed_upload,
    delete_stale_temp_files,
    move_to_avatars,
    sniff_image_type,
    temp_path,
)



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

# ------------------------------------------------------------
# Authorization rules (policies)
# ------------------------------------------------------------

def is_admin(viewer: dict | None) -> bool:
    return viewer is not None and viewer.get("role") == "admin"


def can_view_private_profile(viewer: dict | None, user_id: int) -> bool:
    # Only the user themselves (or an admin) can see private profile fields.
    if viewer is None:
        return False

    return viewer["id"] == user_id or is_admin(viewer)


def can_delete_review(viewer: dict, review: dict) -> bool:
    # The author can delete their own review; an admin can delete any review.
    return viewer["id"] == review["authorId"] or is_admin(viewer)


# ------------------------------------------------------------
# Use cases
# ------------------------------------------------------------

async def get_email(viewer: dict | None, user_id: int) -> str | None:
    if not can_view_private_profile(viewer, user_id):
        return None

    return await get_user_email(user_id)


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
    viewer = require_user(user)

    review = await get_review(review_id)

    if review is None or not can_delete_review(viewer, review):
        return None

    await delete_review(review_id)

    return review



async def change_nickname(user: dict | None, nickname: str) -> dict:
    author = require_user(user)

    nickname = nickname.strip()
    if not nickname:
        raise ValidationError("Nickname cannot be empty.")

    return await update_user_nickname(
        user_id=author["id"],
        nickname=nickname,
    )

async def request_avatar_upload(user: dict | None) -> dict:
    owner = require_user(user)

    # Temporary files are only kept briefly, so abandoned uploads can't fill the disk.
    delete_stale_temp_files()

    upload = create_signed_upload()

    await create_upload(
        upload_id=upload["upload_id"],
        owner_id=owner["id"],
        expires=upload["expires"],
    )

    return upload


async def set_avatar(user: dict | None, upload_id: str) -> dict:
    owner = require_user(user)

    upload = await get_upload(upload_id)

    # Ownership rule: you can only claim an upload URL you requested yourself.
    if upload is None or upload["ownerId"] != owner["id"]:
        raise ValidationError("Upload not found.")

    path = temp_path(upload_id)

    if not path.exists():
        raise ValidationError("The file has not been uploaded yet.")

    # Never trust the client's file name or Content-Type: check the real bytes.
    extension = sniff_image_type(path)

    if extension is None:
        path.unlink(missing_ok=True)
        await delete_upload(upload_id)
        raise ValidationError("Avatar must be a PNG or JPEG image.")

    avatar_url = move_to_avatars(path, extension)
    await delete_upload(upload_id)

    return await update_user_avatar_url(
        user_id=owner["id"],
        avatar_url=avatar_url,
    )
