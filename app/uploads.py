"""The signed upload endpoint. Plain HTTP, not GraphQL.

The client sends the raw file bytes here with a PUT, using the URL
returned by the `requestAvatarUpload` mutation.
"""

from fastapi import APIRouter, HTTPException, Request

from app.storage import (
    MAX_UPLOAD_BYTES,
    is_valid_signature,
    temp_path,
)


router = APIRouter()


@router.put("/uploads/{upload_id}", status_code=204)
async def receive_upload(
    upload_id: str,
    expires: int,
    signature: str,
    request: Request,
):
    # The signature is the authorization: only URLs we issued are accepted,
    # so upload_id can be trusted as a file name (no path traversal).
    if not is_valid_signature(upload_id, expires, signature):
        raise HTTPException(status_code=403, detail="Invalid or expired upload URL")

    path = temp_path(upload_id)

    if path.exists():
        raise HTTPException(status_code=409, detail="Upload URL already used")

    size = 0

    try:
        # Stream to disk chunk by chunk; never hold the whole file in memory.
        with path.open("wb") as file:
            async for chunk in request.stream():
                size += len(chunk)

                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File too large")

                file.write(chunk)
    except BaseException:
        # Failed or aborted upload: never leave a partial file behind.
        path.unlink(missing_ok=True)
        raise
