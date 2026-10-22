"""Globally unique, opaque IDs for the Node interface.

A global ID encodes the type name and the type's own (local) ID,
so `node(id:)` can tell which kind of object to fetch.
"""

import base64
import binascii


def to_global_id(type_name: str, local_id: object) -> str:
    raw = f"{type_name}:{local_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def from_global_id(global_id: str) -> tuple[str, str] | None:
    try:
        raw = base64.urlsafe_b64decode(global_id.encode()).decode()
    except (binascii.Error, UnicodeDecodeError):
        return None

    type_name, separator, local_id = raw.partition(":")

    if not separator or not type_name or not local_id:
        return None

    return type_name, local_id
