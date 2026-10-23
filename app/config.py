import os

from dotenv import load_dotenv


load_dotenv()


APP_ENV = os.getenv(
    "APP_ENV",
    "development",
).strip().lower()

IS_PRODUCTION = APP_ENV == "production"

def read_bool(
    name: str,
    default: bool,
) -> bool:
    raw_value = os.getenv(
        name,
        str(default),
    ).strip().lower()

    if raw_value in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True

    if raw_value in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False

    raise RuntimeError(
        f"{name} must be a Boolean value."
    )

def read_positive_float(
    name: str,
    default: float,
) -> float:
    raw_value = os.getenv(
        name,
        str(default),
    ).strip()

    try:
        value = float(raw_value)
    except ValueError as error:
        raise RuntimeError(
            f"{name} must be a number."
        ) from error

    if value <= 0:
        raise RuntimeError(
            f"{name} must be greater than zero."
        )

    return value

GRAPHQL_REQUEST_TIMEOUT_SECONDS = read_positive_float(
    "GRAPHQL_REQUEST_TIMEOUT_SECONDS",
    default=10.0,
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1",
    ).split(",")
    if host.strip()
]


if not ALLOWED_HOSTS:
    raise RuntimeError(
        "ALLOWED_HOSTS must contain at least one hostname."
    )


FORCE_HTTPS = read_bool(
    "FORCE_HTTPS",
    default=IS_PRODUCTION,
)


ALLOW_GRAPHQL_GET = read_bool(
    "ALLOW_GRAPHQL_GET",
    default=not IS_PRODUCTION,
)

UPLOAD_SECRET = os.getenv(
    "UPLOAD_SECRET",
    "",
).strip()


if not UPLOAD_SECRET:
    raise RuntimeError(
        "UPLOAD_SECRET is required. "
        "Set it in the application environment."
    )


if len(UPLOAD_SECRET.encode("utf-8")) < 32:
    raise RuntimeError(
        "UPLOAD_SECRET must contain at least 32 bytes."
    )