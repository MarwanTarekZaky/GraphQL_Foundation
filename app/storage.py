"""A tiny local stand-in for a storage provider such as Amazon S3.

It signs upload URLs, keeps uploaded bytes in a temporary area,
and moves files to permanent storage only when the app claims them.
"""

import hashlib
import hmac
import os
import time
from pathlib import Path
from uuid import uuid4


UPLOAD_SECRET = os.getenv("UPLOAD_SECRET", "dev-only-change-me").encode()
UPLOAD_URL_TTL_SECONDS = 5 * 60
TEMP_FILE_TTL_SECONDS = 60 * 60
MAX_UPLOAD_BYTES = 2 * 1024 * 1024

MEDIA_DIR = Path("media")
TEMP_DIR = MEDIA_DIR / "tmp"
AVATAR_DIR = MEDIA_DIR / "avatars"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# The first bytes of a file tell us its real type, whatever the client claims.
IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
}


def sign(upload_id: str, expires: int) -> str:
    message = f"{upload_id}:{expires}".encode()
    return hmac.new(UPLOAD_SECRET, message, hashlib.sha256).hexdigest()


def create_signed_upload() -> dict:
    upload_id = uuid4().hex
    expires = int(time.time()) + UPLOAD_URL_TTL_SECONDS

    return {
        "upload_id": upload_id,
        "expires": expires,
        "path": f"/uploads/{upload_id}?expires={expires}&signature={sign(upload_id, expires)}",
    }


def is_valid_signature(upload_id: str, expires: int, signature: str) -> bool:
    if expires < time.time():
        return False

    return hmac.compare_digest(sign(upload_id, expires), signature)


def temp_path(upload_id: str) -> Path:
    return TEMP_DIR / upload_id


def sniff_image_type(path: Path) -> str | None:
    with path.open("rb") as file:
        head = file.read(8)

    for signature, extension in IMAGE_SIGNATURES.items():
        if head.startswith(signature):
            return extension

    return None


def move_to_avatars(path: Path, extension: str) -> str:
    final_path = AVATAR_DIR / f"{path.name}.{extension}"
    path.replace(final_path)
    return f"/media/avatars/{final_path.name}"


def delete_stale_temp_files():
    cutoff = time.time() - TEMP_FILE_TTL_SECONDS

    for path in TEMP_DIR.iterdir():
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
