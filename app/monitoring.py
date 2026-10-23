"""Lightweight performance monitoring.

Times each GraphQL operation and counts the MongoDB commands it sends.
This is a small local stand-in for a production observability system.
"""

import time

from contextvars import ContextVar

from pymongo import monitoring
from strawberry.extensions import SchemaExtension


# The counter for the operation currently running.
# It is None outside a GraphQL operation.
current_db_queries: ContextVar[list[int] | None] = ContextVar(
    "current_db_queries",
    default=None,
)


class DatabaseQueryCounter(monitoring.CommandListener):
    """PyMongo calls started() for each command sent to MongoDB."""

    def started(self, event):
        counter = current_db_queries.get()

        if counter is not None:
            counter[0] += 1

    def succeeded(self, event):
        pass

    def failed(self, event):
        pass


class OperationStats(SchemaExtension):
    """Collect execution duration and MongoDB query count safely."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # These defaults are important.
        # Parsing may fail before on_operation() begins.
        self.db_queries = [0]
        self.duration_ms = 0.0

    def on_operation(self):
        # Reset data for this execution.
        self.db_queries = [0]
        self.duration_ms = 0.0

        token = current_db_queries.set(self.db_queries)
        started_at = time.perf_counter()

        try:
            yield
        finally:
            self.duration_ms = (
                time.perf_counter() - started_at
            ) * 1000

            current_db_queries.reset(token)

    def get_results(self):
        return {
            "stats": {
                "dbQueries": self.db_queries[0],
                "durationMs": round(self.duration_ms, 1),
            }
        }