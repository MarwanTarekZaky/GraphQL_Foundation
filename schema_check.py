"""Compare the live schema with the committed snapshot in schema.graphql.

    python schema_check.py           # report breaking / dangerous changes
    python schema_check.py --update  # save the live schema as the new snapshot
"""

import sys
from pathlib import Path

from graphql import build_schema, find_breaking_changes, find_dangerous_changes

from app.schema import schema


SNAPSHOT = Path("schema.graphql")


def main():
    live_sdl = schema.as_str()

    if "--update" in sys.argv or not SNAPSHOT.exists():
        SNAPSHOT.write_text(live_sdl + "\n")
        print(f"Snapshot saved to {SNAPSHOT}.")
        return

    old_schema = build_schema(SNAPSHOT.read_text())
    new_schema = build_schema(live_sdl)

    breaking = find_breaking_changes(old_schema, new_schema)
    dangerous = find_dangerous_changes(old_schema, new_schema)

    for change in breaking:
        print(f"BREAKING   {change.description}")

    for change in dangerous:
        print(f"DANGEROUS  {change.description}")

    if not breaking and not dangerous:
        print("No breaking or dangerous changes.")

    sys.exit(1 if breaking else 0)


main()
