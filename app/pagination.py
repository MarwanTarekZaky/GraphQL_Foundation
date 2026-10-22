"""Opaque cursors for cursor-based pagination.

Clients must treat cursors as meaningless strings. Encoding them hides
the real position (a MongoDB ObjectId), so the backend can change its
pagination strategy later without breaking clients.
"""

import base64
import binascii

from bson import ObjectId
from bson.errors import InvalidId


CURSOR_PREFIX = "cursor:"


def encode_cursor(object_id: ObjectId) -> str:
    raw = f"{CURSOR_PREFIX}{object_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> ObjectId | None:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    except (binascii.Error, UnicodeDecodeError):
        return None

    if not raw.startswith(CURSOR_PREFIX):
        return None

    try:
        return ObjectId(raw.removeprefix(CURSOR_PREFIX))
    except InvalidId:
        return None
